package net.sourceforge.jvlt.ui.vocabulary;

import java.awt.Dimension;
import java.awt.Font;
import java.awt.GridBagLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.awt.event.MouseAdapter;
import java.awt.event.MouseEvent;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Iterator;
import java.util.List;
import java.util.Vector;

import javax.swing.Box;
import javax.swing.JButton;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JSplitPane;
import javax.swing.event.ListSelectionEvent;
import javax.swing.event.ListSelectionListener;
import javax.swing.table.TableColumnModel;

import org.apache.log4j.Logger;

import net.sourceforge.jvlt.JVLT;
import net.sourceforge.jvlt.actions.AddDictObjectAction;
import net.sourceforge.jvlt.actions.EditDictObjectAction;
import net.sourceforge.jvlt.actions.RemoveExamplesAction;
import net.sourceforge.jvlt.core.Dict;
import net.sourceforge.jvlt.core.Example;
import net.sourceforge.jvlt.event.DictUpdateListener;
import net.sourceforge.jvlt.event.FilterListener;
import net.sourceforge.jvlt.event.SelectionListener;
import net.sourceforge.jvlt.event.SelectionNotifier;
import net.sourceforge.jvlt.event.FilterListener.FilterEvent;
import net.sourceforge.jvlt.metadata.MetaData;
import net.sourceforge.jvlt.model.JVLTModel;
import net.sourceforge.jvlt.ui.components.CustomTextField;
import net.sourceforge.jvlt.ui.dialogs.AbstractDialog;
import net.sourceforge.jvlt.ui.dialogs.CustomDialog;
import net.sourceforge.jvlt.ui.table.CustomFontCellRenderer;
import net.sourceforge.jvlt.ui.table.SortableTable;
import net.sourceforge.jvlt.ui.table.SortableTableModel;
import net.sourceforge.jvlt.ui.table.SortableTableModel.SortOrder;
import net.sourceforge.jvlt.ui.utils.CustomAction;
import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.ui.utils.GUIUtils;
import net.sourceforge.jvlt.utils.I18nService;
import net.sourceforge.jvlt.utils.UIConfig;
import net.sourceforge.jvlt.utils.Utils;

public class ExamplePanel extends JPanel implements ActionListener,
		ListSelectionListener, DictUpdateListener, SelectionListener {
	private static final long serialVersionUID = 1L;

	private static final CustomFontCellRenderer ORIGINAL_RENDERER;

	private static Logger logger = Logger.getLogger(ExamplePanel.class);

	static {
		Font font;
		ORIGINAL_RENDERER = new CustomFontCellRenderer();
		font = ((UIConfig) JVLT.getConfig()).getFontProperty("ui_orth_font");
		if (font != null) {
			ORIGINAL_RENDERER.setCustomFont(font);
		}
	}

	private final ArrayList<FilterListener<Example>> _filter_listeners;
	private final JVLTModel _model;
	private Dict _dict;
	private List<Example> _current_examples;
	private final SelectionNotifier _notifier;
	private final ExampleFilter _filter;

	private SortableTable<Example> _example_table;
	private SortableTableModel<Example> _table_model;
	private CustomTextField _filter_field;
	private CustomAction _add_action;
	private CustomAction _edit_action;
	private CustomAction _remove_action;
	private ExampleInfoPanel _info_panel;

	public ExamplePanel(JVLTModel model, SelectionNotifier notifier) {
		_filter_listeners = new ArrayList<FilterListener<Example>>();
		_current_examples = new ArrayList<Example>();
		_notifier = notifier;
		_model = model;
		_filter = new ExampleFilter();
		_filter.setMatchCase(false);
		_dict = _model.getDict();
		_model.getDictModel().addDictUpdateListener(this);
		_model.getQueryModel().addDictUpdateListener(this);
		notifier.addSelectionListener(this);
		init();
		updateActions();
	}

	public void saveState(UIConfig config) {
		String[] columns = _table_model.getColumnNames();
		config.setProperty("example_table_column_names", columns);

		Double[] col_widths = new Double[columns.length];
		TableColumnModel col_model = _example_table.getColumnModel();
		for (int i = 0; i < columns.length; i++) {
			col_widths[i] = new Double(col_model.getColumn(i).getWidth());
		}

		config.setProperty("example_table_column_widths", col_widths);

		SortableTableModel.Directive dir = _table_model.getSortingDirective();
		config.setProperty("example_table_sorting", Utils
				.arrayToString(new Integer[] { dir.getColumn(),
						dir.getDirection().toInt() }));
	}

	public void loadState(UIConfig config) {
		String[] col_names = config.getStringListProperty(
				"example_table_column_names", new String[] { "Text" });
		_table_model.setColumnNames(col_names);

		SortableTableModel.Directive dir = new SortableTableModel.Directive();
		String[] dir_string = config.getStringListProperty(
				"example_table_sorting", new String[] {
						String.valueOf(dir.getColumn()),
						String.valueOf(dir.getDirection().toInt()) });
		if (dir_string.length == 2) {
			try {
				int col = Integer.parseInt(dir_string[0]);
				int direction = Integer.parseInt(dir_string[1]);
				dir.setColumn(col);
				dir.setDirection(SortOrder.valueOf(direction));
			} catch (NumberFormatException e) {
				logger.warn("Could not read sorting info for example table", e);
			}
		}
		_table_model.setSortingDirective(dir);
		
		/*
		 * Load column widths. This must be done after setting the sorting
		 * directive, as otherwise the widths are reset.
		 */
		double[] col_widths = config.getNumberListProperty(
				"example_table_column_widths", new double[] { 50 });
		if (col_widths.length != _table_model.getColumnCount()) {
			return;
		}

		TableColumnModel col_model = _example_table.getColumnModel();
		for (int i = 0; i < col_widths.length; i++) {
			col_model.getColumn(i).setPreferredWidth((int) col_widths[i]);
		}
	}

	public void objectSelected(SelectionEvent e) {
		Object obj = e.getElement();
		if (obj instanceof Example) {
			Example example = (Example) obj;
			if (e.getSource() == _example_table) {
				if (_current_examples.size() > 0) {
					editExample(_current_examples.get(0));
				}
			} else {
				if (!_table_model.containsObject(example)) {
					_filter.setFilterString("");
					_filter_field.setText("");
					applyFilter();
				}
				_example_table.setSelectedObject(example);
			}
		}
	}

	public void valueChanged(ListSelectionEvent e) {
		if (!e.getValueIsAdjusting()) {
			List<Example> objs = _example_table.getSelectedObjects();
			if (objs.size() == 0) {
				return;
			}

			setCurrentExamples(objs);
			updateActions();
		}
	}

	public void actionPerformed(ActionEvent e) {
		if (e.getActionCommand().equals("add")) {
			Example new_example = new Example(_dict.getNextUnusedExampleID());
			ExampleDialogData data = new ExampleDialogData(new_example, _dict);
			int result = CustomDialog.showDialog(data, this, I18nService
					.getString("Labels", "add_example"));
			if (result == AbstractDialog.OK_OPTION) {
				AddDictObjectAction action = new AddDictObjectAction(
						new_example);
				action.setMessage(I18nService.getString("Actions", "add_example"));
				_model.getDictModel().executeAction(action);
			}
		} else if (e.getActionCommand().equals("edit")) {
			if (_current_examples.size() > 0) {
				editExample(_current_examples.get(0));
			}
		} else if (e.getActionCommand().equals("remove")) {
			if (_current_examples.size() > 0) {
				int result = JOptionPane.showConfirmDialog(this, I18nService
						.getString("Messages", "remove_examples"), I18nService
						.getString("Labels", "confirm"),
						JOptionPane.YES_NO_OPTION);
				if (result == JOptionPane.YES_OPTION) {
					RemoveExamplesAction action = new RemoveExamplesAction(
							_current_examples);
					action.setMessage(I18nService.getString("Actions",
							"remove_example"));
					_model.getDictModel().executeAction(action);
				}
			}
		} else if (e.getActionCommand().equals("filter")
				|| e.getActionCommand().equals("ok")) {
			String str = _filter_field.getText();
			_filter.setFilterString(str);
			applyFilter();
		} else if (e.getActionCommand().equals("cancel")) {
			_filter_field.setText("");
			_filter.setFilterString("");
			applyFilter();
		}
	}

	public synchronized void dictUpdated(DictUpdateEvent event) {
		if (event instanceof ExampleDictUpdateEvent) {
			ExampleDictUpdateEvent eevent = (ExampleDictUpdateEvent) event;
			Collection<Example> examples = eevent.getExamples();
			if (eevent.getType() == ExampleDictUpdateEvent.EXAMPLES_ADDED) {
				Example example = null;
				for (Iterator<Example> it = examples.iterator(); it.hasNext();) {
					example = it.next();
					if (_filter.isExampleMatching(example)) {
						_table_model.addObject(example);
					}
				}
				if (example != null && _table_model.containsObject(example)) {
					_example_table.setSelectedObject(example);
				}

				fireFilterEvent(new FilterEvent<Example>(this, _table_model
						.getObjects()));
			} else if (eevent.getType() == ExampleDictUpdateEvent.EXAMPLES_CHANGED) {
				if (examples.size() < 1) {
					return;
				}

				List<Example> objs = _example_table.getSelectedObjects();
				applyFilter();
				if (objs.size() > 0 && _table_model.containsObject(objs.get(0))) {
					_example_table.setSelectedObject(objs.get(0));
				}
			} else if (eevent.getType() == ExampleDictUpdateEvent.EXAMPLES_REMOVED) {
				for (Example example : examples) {
					_table_model.removeObject(example);
				}

				fireFilterEvent(new FilterEvent<Example>(this, _table_model
						.getObjects()));
			}
		} else if (event instanceof NewDictDictUpdateEvent) {
			_dict = _model.getDict();
			setCurrentExamples(new ArrayList<Example>());
			applyFilter();
		}
	}

	public void addFilterListener(FilterListener<Example> fl) {
		_filter_listeners.add(fl);
	}

	public void removeFilterListener(FilterListener<Example> fl) {
		_filter_listeners.remove(fl);
	}

	private void fireFilterEvent(FilterEvent<Example> ev) {
		Iterator<FilterListener<Example>> it = _filter_listeners.iterator();
		while (it.hasNext()) {
			it.next().filterApplied(ev);
		}
	}

	private void init() {
		_filter_field = new CustomTextField();
		_filter_field.setActionCommand("filter");
		_filter_field.addActionListener(this);
		JPanel filter_panel = new JPanel();
		filter_panel.setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 0.0, 0.0);
		filter_panel.add(_filter_field.getLabel(), cc);
		cc.update(1, 0, 1.0, 0.0);
		filter_panel.add(_filter_field, cc);
		cc.update(2, 0, 0.0, 0.0);
		filter_panel.add(
				new JButton(GUIUtils.createIconAction(this, "cancel")), cc);
		cc.update(3, 0, 0.0, 0.0);
		filter_panel
				.add(new JButton(GUIUtils.createIconAction(this, "ok")), cc);

		// ----------
		// Example table
		// ----------
		MetaData data = _model.getDictModel().getMetaData(Example.class);
		_table_model = new SortableTableModel<Example>(data);
		_table_model.setColumnNames(new String[] { "Text" });
		_example_table = new SortableTable<Example>(_table_model);
		_example_table.setCellRenderer("Text", ORIGINAL_RENDERER);
		_example_table.getSelectionModel().addListSelectionListener(this);
		_example_table.setShowTooltips(JVLT.getConfig().getBooleanProperty(
				"Table.showTooltips", true));
		_example_table.addMouseListener(new MouseAdapter() {
			@Override
			public void mouseClicked(MouseEvent e) {
				if (e.getClickCount() != 2) {
					return;
				}

				int index = _example_table.rowAtPoint(e.getPoint());
				if (index < 0) {
					return;
				}

				Example example = _table_model.getObjectAt(index);
				editExample(example);
			}
		});
		JScrollPane scrpane = new JScrollPane();
		scrpane.getViewport().setView(_example_table);
		// Handle double click events inside the example list.
		SelectionNotifier notifier = new SelectionNotifier();
		notifier.addSelectionListener(this);

		// ----------
		// Buttons for modifying example list
		// ----------
		_add_action = GUIUtils.createTextAction(this, "add");
		_edit_action = GUIUtils.createTextAction(this, "edit");
		_remove_action = GUIUtils.createTextAction(this, "remove");

		JPanel example_button_panel = new JPanel();
		example_button_panel.setLayout(new GridBagLayout());
		cc.update(0, 0, 0.0, 0.0);
		example_button_panel.add(new JButton(_add_action), cc);
		cc.update(0, 1);
		example_button_panel.add(new JButton(_edit_action), cc);
		cc.update(0, 2);
		example_button_panel.add(new JButton(_remove_action), cc);
		cc.update(0, 3, 0.0, 1.0);
		example_button_panel.add(Box.createVerticalGlue(), cc);

		_info_panel = new ExampleInfoPanel(_model, _notifier);

		JSplitPane split_pane = new JSplitPane(JSplitPane.VERTICAL_SPLIT,
				scrpane, _info_panel);
		split_pane.setDividerLocation(0.7);
		_info_panel.setPreferredSize(new Dimension(500, 200));
		scrpane.setPreferredSize(new Dimension(500, 200));

		setLayout(new GridBagLayout());
		cc.reset();
		cc.update(0, 0, 1.0, 0.0);
		add(filter_panel, cc);
		cc.update(0, 1, 1.0, 1.0);
		add(split_pane, cc);
		cc.update(1, 1, 0.0, 1.0);
		add(example_button_panel, cc);
	}

	private void editExample(Example example) {
		Example new_data = (Example) example.clone();
		ExampleDialogData data = new ExampleDialogData(new_data, _dict);
		int result = CustomDialog.showDialog(data, this, I18nService.getString(
				"Labels", "edit_example"));
		if (result == AbstractDialog.OK_OPTION) {
			EditDictObjectAction action = new EditDictObjectAction(example,
					new_data);
			action.setMessage(I18nService.getString("Actions", "edit_example"));
			_model.getDictModel().executeAction(action);
		}
	}

	private void setCurrentExamples(List<Example> examples) {
		_current_examples = examples;
		if (examples.size() > 0) {
			_info_panel.setExample(examples.get(0));
		}
	}

	private void applyFilter() {
		Collection<Example> examples = _dict.getExamples();
		Collection<Example> me = _filter.getMatchingExamples(examples);
		_table_model.setObjects(me);
		fireFilterEvent(new FilterEvent<Example>(this, me));
	}

	private void updateActions() {
		boolean element_selected = (_example_table.getSelectedObjects().size() > 0);

		_edit_action.setEnabled(element_selected);
		_remove_action.setEnabled(element_selected);
	}
}

abstract class Filter {
	protected String _filter_string;

	public Filter(String filter_string) {
		_filter_string = filter_string;
	}

	public Filter() {
		this("");
	}

	public String getFilterString() {
		return _filter_string;
	}

	public void setFilterString(String val) {
		_filter_string = val;
	}
}

class ExampleFilter extends Filter {
	boolean _match_case = true;

	public ExampleFilter(String filter_string) {
		super(filter_string);
	}

	public ExampleFilter() {
		this("");
	}

	public boolean isExampleMatching(Example example) {
		if (_filter_string.equals("")) {
			return true;
		} else if (_match_case) {
			return (example.toString().indexOf(_filter_string) != -1);
		} else {
			return (example.toString().toLowerCase().indexOf(
					_filter_string.toLowerCase()) != -1);
		}
	}

	public Collection<Example> getMatchingExamples(Collection<Example> examples) {
		if (_filter_string.equals("")) {
			return examples;
		}

		Vector<Example> example_vec = new Vector<Example>();
		for (Example example : examples) {
			if (isExampleMatching(example)) {
				example_vec.add(example);
			}
		}

		return example_vec;
	}

	public void setMatchCase(boolean match) {
		_match_case = match;
	}
}
