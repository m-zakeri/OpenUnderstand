package net.sourceforge.jvlt.ui.vocabulary;

import java.awt.BorderLayout;
import java.awt.Dimension;
import java.awt.Font;
import java.awt.GridBagConstraints;
import java.awt.GridBagLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.text.ParseException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;

import javax.swing.Box;
import javax.swing.JButton;
import javax.swing.JEditorPane;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JTextArea;
import javax.swing.border.EtchedBorder;
import javax.swing.border.TitledBorder;
import javax.swing.event.CaretEvent;
import javax.swing.event.CaretListener;
import javax.swing.event.ListSelectionEvent;
import javax.swing.event.ListSelectionListener;
import javax.swing.event.TreeSelectionEvent;
import javax.swing.event.TreeSelectionListener;
import javax.swing.table.TableColumnModel;
import javax.swing.text.AttributeSet;
import javax.swing.text.BadLocationException;
import javax.swing.text.Document;
import javax.swing.text.PlainDocument;

import net.sourceforge.jvlt.JVLT;
import net.sourceforge.jvlt.core.Dict;
import net.sourceforge.jvlt.core.DictException;
import net.sourceforge.jvlt.core.Entry;
import net.sourceforge.jvlt.core.Example;
import net.sourceforge.jvlt.core.Sense;
import net.sourceforge.jvlt.core.Example.TextFragment;
import net.sourceforge.jvlt.query.EntryFilter;
import net.sourceforge.jvlt.query.StringQueryItem;
import net.sourceforge.jvlt.ui.components.CustomTextField;
import net.sourceforge.jvlt.ui.dialogs.CustomDialogData;
import net.sourceforge.jvlt.ui.dialogs.InvalidDataException;
import net.sourceforge.jvlt.ui.dialogs.MessageDialog;
import net.sourceforge.jvlt.ui.utils.CustomAction;
import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.ui.utils.GUIUtils;
import net.sourceforge.jvlt.utils.ExampleBuilder;
import net.sourceforge.jvlt.utils.I18nService;
import net.sourceforge.jvlt.utils.UIConfig;
import net.sourceforge.jvlt.utils.SimpleHTMLParser;
import net.sourceforge.jvlt.utils.Utils;

public class ExampleDialogData extends CustomDialogData implements
		ActionListener, CaretListener, ListSelectionListener,
		TreeSelectionListener {
	private final Example _example;
	private final Dict _dict;
	private final EntryFilter _entry_filter;
	private final StringQueryItem _entry_filter_item;
	/**
	 * Index of the first character in the current selection (-1 if there is no
	 * selection).
	 */
	private int _current_selection_start;
	/**
	 * Index of the first character after the current selection (-1 if there is
	 * no selection).
	 */
	private int _current_selection_end;

	private JPanel _add_senses_panel;
	private JEditorPane _preview_pane;
	private JLabel _available_senses_label;
	private JLabel _current_senses_label;
	private ExampleTextField _example_field;
	private CustomTextField _filter_field;
	private JTextArea _translation_field;
	private ExampleSenseTable _current_senses_table;
	private DictEntryTree _selected_senses_tree;
	private CustomAction _add_sense_action;
	private CustomAction _remove_sense_action;

	public ExampleDialogData(Example example, Dict dict) {
		_example = example;
		_dict = dict;
		_current_selection_start = -1;
		_current_selection_end = -1;

		/* set up entry filter */
		_entry_filter_item = new StringQueryItem("Orthography",
				StringQueryItem.CONTAINS, "");
		_entry_filter_item.setMatchCase(false);
		_entry_filter = new EntryFilter();
		_entry_filter.getQuery().addItem(_entry_filter_item);

		init();
		updatePreviewPane();
		updateAddSensesPanel();
		updateActions();
		updateStatusLabels();
	}

	@Override
	public void updateData() throws InvalidDataException {
		if (_example.getSenses().length == 0) {
			throw new InvalidDataException(I18nService.getString("Messages",
					"no_links"));
		}

		SimpleHTMLParser parser = new SimpleHTMLParser();
		try {
			parser.parse(_translation_field.getText());
			parser.parse(_example.getHTMLText());
		} catch (ParseException e) {
			throw new InvalidDataException(I18nService.getString("Messages",
					"invalid_html", new Object[] { e.getMessage() }));
		}

		_example.setTranslation(_translation_field.getText());
		Example e = _dict.getExample(_example);
		if (e != null && !e.getID().equals(_example.getID())) {
			throw new InvalidDataException(I18nService.getString("Messages",
					"duplicate_example"));
		}
	}

	public void caretUpdate(CaretEvent e) {
		String text = _example_field.getSelectedText();
		if (text == null || text.equals("")) {
			_current_selection_start = -1;
			_current_selection_end = -1;
		} else if (e.getDot() > e.getMark()) {
			_current_selection_start = e.getMark();
			_current_selection_end = e.getDot();
		} else {
			_current_selection_start = e.getDot();
			_current_selection_end = e.getMark();
		}

		updateAddSensesPanel();
		updatePreviewPane();
	}

	public void valueChanged(ListSelectionEvent e) {
		if (!e.getValueIsAdjusting()) {
			updateActions();
			updatePreviewPane();
			updateStatusLabels();
		}
	}

	public void valueChanged(TreeSelectionEvent ev) {
		updateActions();
		updateStatusLabels();
	}

	public void actionPerformed(ActionEvent e) {
		if (e.getActionCommand().equals("add")) {
			ExampleBuilder builder = new ExampleBuilder(_example);
			Object obj = _selected_senses_tree.getSelectedObject();
			int from = _current_selection_start;
			int to = _current_selection_end - 1;
			try {
				if (obj instanceof Sense) {
					builder.addSense((Sense) obj, from, to);
				} else if (obj instanceof Entry) {
					// If the word only has one meaning, add the meaning.
					// Otherwise show an error dialog.
					Entry entry = (Entry) obj;
					if (entry.getSenses().length > 1) {
						MessageDialog
								.showDialog(_content_pane,
										MessageDialog.WARNING_MESSAGE,
										I18nService.getString("Messages",
														"select_meaning"));
					} else if (entry.getSenses().length == 0) {
						MessageDialog.showDialog(_content_pane,
								MessageDialog.WARNING_MESSAGE, I18nService
										.getString("Messages", "no_meaning"));
					} else {
						builder.addSense(entry.getSenses()[0], from, to);
					}
				}
			} catch (DictException ex) {
				MessageDialog.showDialog(_content_pane,
						MessageDialog.WARNING_MESSAGE, ex.getMessage());
			}

			_current_senses_table.update();
			if (_example_field.getCaret().getDot() == 0) {
				_example_field.getCaret().setDot(_current_selection_end);
			} else {
				_example_field.getCaret().setDot(0);
				// updatePreviewPane() is called automatically.
			}
		} else if (e.getActionCommand().equals("remove")) {
			ExampleBuilder builder = new ExampleBuilder(_example);
			builder.removeTextFragment(_current_senses_table
					.getSelectedTextFragment());

			_current_senses_table.update();
			updatePreviewPane();
		} else if (e.getActionCommand().equals("filter")) {
			updateSelectedSensesTree();
		}
	}

	@Override
	public void prepareToShow() {
		_example_field.requestFocusInWindow();
	}

	@Override
	protected void loadState(UIConfig config) {
		_content_pane.setPreferredSize(config.getDimensionProperty(
				"ExampleDialog.size", new Dimension(500, 500)));
		
		/* restore column widths */
		double[] col_widths = config.getNumberListProperty(
				"ExampleDialog.SensesTable.columnWidths",
				new double[] { 50, 50, 50 });
		if (col_widths.length == _current_senses_table.getColumnCount()) {
			TableColumnModel col_model = _current_senses_table.getColumnModel();
			for (int i = 0; i < col_widths.length; i++) {
				col_model.getColumn(i).setPreferredWidth((int) col_widths[i]);
			}
		}
	}

	@Override
	protected void saveState(UIConfig config) {
		config.setProperty("ExampleDialog.size", _content_pane.getSize());
		
		/* save column widths */
		Double[] col_widths = new Double[_current_senses_table.getColumnCount()];
		TableColumnModel col_model = _current_senses_table.getColumnModel();
		for (int i = 0; i < _current_senses_table.getColumnCount(); i++) {
			col_widths[i] = new Double(col_model.getColumn(i).getWidth());
		}
		config.setProperty("ExampleDialog.SensesTable.columnWidths",
						col_widths);
	}

	private void init() {
		Font orth_font = ((UIConfig) JVLT.getConfig()).getFontProperty(
				"ui_orth_font");

		// -----------
		// Setup the preview pane which displays the example and its
		// translation. For the example, it is shown which parts are connected
		// to a sense and which part is currently selected.
		// -----------
		_preview_pane = new JEditorPane();
		_preview_pane.setEditable(false);
		_preview_pane.setContentType("text/html");
		JScrollPane preview_scrpane = new JScrollPane(_preview_pane);
		preview_scrpane
				.setBorder(new TitledBorder(new EtchedBorder(
						EtchedBorder.LOWERED), I18nService.getString("Labels",
						"preview")));

		// ----------
		// Example text field
		// ----------
		_example_field = new ExampleTextField();
		_example_field.addCaretListener(this);
		JScrollPane example_scrpane = new JScrollPane(_example_field);

		// ----------
		// Translation text field.
		// ----------
		_translation_field = new JTextArea();
		_translation_field.addCaretListener(this);
		JScrollPane translation_scrpane = new JScrollPane(_translation_field);

		// ----------
		// List displaying the senses connected with the currently
		// active example
		// ----------
		_current_senses_table = new ExampleSenseTable(_example);
		_current_senses_table.getSelectionModel()
				.addListSelectionListener(this);
		_current_senses_table.setShowTooltips(JVLT.getConfig()
				.getBooleanProperty("Table.showTooltips", true));
		JScrollPane current_senses_scrpane = new JScrollPane();
		current_senses_scrpane.getViewport().setView(_current_senses_table);
		_current_senses_label = new JLabel();

		// ----------
		// Tree view displaying the senses of the entry corresponding to the
		// currently selected word in the text field (in case there is any).
		// ----------
		_selected_senses_tree = new DictEntryTree();
		_selected_senses_tree.addTreeSelectionListener(this);
		JScrollPane selected_senses_scrpane = new JScrollPane();
		selected_senses_scrpane.getViewport().setView(_selected_senses_tree);
		_available_senses_label = new JLabel();

		_filter_field = new CustomTextField();
		_filter_field.setActionCommand("filter");
		_filter_field.addActionListener(this);
		if (orth_font != null) {
			_filter_field.setFont(orth_font);
		}
		JPanel filter_panel = new JPanel();
		filter_panel.setLayout(new BorderLayout(5, 0));
		filter_panel.add(_filter_field.getLabel(), BorderLayout.WEST);
		filter_panel.add(_filter_field, BorderLayout.CENTER);

		_add_sense_action = GUIUtils.createTextAction(this, "add");
		_remove_sense_action = GUIUtils.createTextAction(this, "remove");

		_add_senses_panel = new JPanel();
		_add_senses_panel.setBorder(new TitledBorder(new EtchedBorder(
				EtchedBorder.LOWERED), I18nService.getString("Labels",
				"create_link")));
		_add_senses_panel.setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1.0, 0.0);
		_add_senses_panel.add(new JLabel(I18nService.getString("Messages",
				"add_senses_help")), cc);
		cc.update(0, 1, 1.0, 0.0);
		_add_senses_panel.add(filter_panel, cc);
		cc.update(0, 2, 1.0, 1.0, 1, 2);
		_add_senses_panel.add(selected_senses_scrpane, cc);
		cc.update(1, 2, 0.0, 0.0, 1, 1);
		_add_senses_panel.add(new JButton(_add_sense_action), cc);
		cc.update(1, 3, 0.0, 1.0);
		_add_senses_panel.add(Box.createVerticalGlue(), cc);
		cc.update(0, 4, 1.0, 0.0, 2, 1);
		_add_senses_panel.add(_available_senses_label, cc);

		JPanel senses_panel = new JPanel();
		senses_panel.setLayout(new GridBagLayout());
		cc.reset();
		cc.update(0, 0, 1.0, 1.0, 1, 2);
		senses_panel.add(current_senses_scrpane, cc);
		cc.update(1, 0, 0.0, 0.0, 1, 1);
		senses_panel.add(new JButton(_remove_sense_action), cc);
		cc.update(1, 1, 0.0, 1.0);
		senses_panel.add(Box.createVerticalGlue(), cc);
		cc.update(0, 2, 1.0, 0.0, 2, 1);
		senses_panel.add(_current_senses_label, cc);
		senses_panel.setBorder(new TitledBorder(new EtchedBorder(
				EtchedBorder.LOWERED), I18nService.getString("Labels", "links")));

		_content_pane = new JPanel();
		_content_pane.setLayout(new GridBagLayout());
		cc.reset();
		cc.update(0, 0, 1.0, 1.0, GridBagConstraints.REMAINDER, 1);
		_content_pane.add(preview_scrpane, cc);
		cc.update(0, 1, 0.5, 0.0, 1, 1);
		_content_pane.add(GUIUtils.getLabel("example", _example_field), cc);
		cc.update(0, 2, 0.5, 1.0);
		_content_pane.add(example_scrpane, cc);
		cc.update(1, 1, 0.5, 0.0);
		_content_pane.add(GUIUtils.getLabel("translation", _translation_field),
				cc);
		cc.update(1, 2, 0.5, 1.0);
		_content_pane.add(translation_scrpane, cc);
		cc.update(0, 3, 1.0, 1.0, GridBagConstraints.REMAINDER, 1);
		_content_pane.add(senses_panel, cc);
		cc.update(0, 4);
		_content_pane.add(_add_senses_panel, cc);

		// ----------
		// Init data
		// ----------
		_example_field.setExample(_example);
		_translation_field.setText(_example.getTranslation());
	}

	private void updatePreviewPane() {
		// ---------
		// Update example preview label. If there is selected text in
		// _example_field then this text is highlighted. Otherwise, the text
		// fragments that are linked to a sense are highlighted.
		// ---------
		Font html_font = ((UIConfig) JVLT.getConfig()).getFontProperty(
				"html_font");
		Font orth_font = ((UIConfig) JVLT.getConfig()).getFontProperty(
				"orth_font");
		StringBuffer buffer = new StringBuffer();
		buffer.append("<html>");
		if (html_font == null) {
			buffer.append("<body>");
		} else {
			buffer.append("<body style=\"font-family:" + html_font.getFamily()
					+ "; font-size:" + html_font.getSize() + ";\">");
		}
		buffer.append("<table width=\"100%\" cellpadding=\"0\""
				+ "cellspacing=\"0\">");
		buffer.append("<tr>");

		//
		// Example text
		//
		if (orth_font == null) {
			buffer.append("<td>");
		} else {
			buffer.append("<td style=\"font-family: " + orth_font.getFamily()
					+ "\">");
		}

		if (_current_selection_start < 0 || _current_selection_end < 0) {
			Example.TextFragment selected_fragment = _current_senses_table
					.getSelectedTextFragment();
			Example.TextFragment[] fragments = _example.getTextFragments();
			for (TextFragment fragment : fragments) {
				if (fragment.getSense() == null) {
					buffer.append(fragment.getText());
				} else {
					buffer.append("<font color=\"");
					if (selected_fragment == fragment) {
						buffer.append("#0000ff");
					} else {
						buffer.append("#00ff00");
					}
					buffer.append("\">" + fragment.getText() + "</font>");
				}
			}
		} else {
			String str = _example.getText();
			String prefix = str.substring(0, _current_selection_start);
			String mid = str.substring(_current_selection_start,
					_current_selection_end);
			String suffix = str.substring(_current_selection_end, str.length());
			buffer.append(prefix + "<font color=\"#ff0000\">" + mid + "</font>"
					+ suffix);
		}
		buffer.append("</td>");

		//
		// Example translation
		//
		String translation = _translation_field.getText();
		if (translation != null && !translation.equals("")) {
			buffer.append("<td style=\"margin:10; width:20;\"></td>");
			buffer.append("<td>");
			buffer.append(translation);
			buffer.append("</td>");
		}

		buffer.append("</tr>");
		buffer.append("</table>");
		buffer.append("</body>");
		buffer.append("</html>");
		_preview_pane.setText(buffer.toString());
	}

	private void updateAddSensesPanel() {
		if (_current_selection_start < 0 || _current_selection_end < 0) {
			_add_senses_panel.setEnabled(false);
			_filter_field.setEnabled(false);
			_selected_senses_tree.setEnabled(false);
			_filter_field.setText("");
		} else {
			_add_senses_panel.setEnabled(true);
			_filter_field.setEnabled(true);
			_selected_senses_tree.setEnabled(true);
			String text = _example.getText().substring(
					_current_selection_start, _current_selection_end);
			_filter_field.setText(text);
		}

		updateSelectedSensesTree();
	}

	private void updateSelectedSensesTree() {
		String text = _filter_field.getText();
		_entry_filter_item.setValue(text);
		if (text == null || text.equals("")) {
			_selected_senses_tree.clear();
		} else {
			/*
			 * Add matching entries, even those already linked (in
			 * order to allow linking the word more than once).
			 */
			List<Entry> entries = _entry_filter.getMatchingEntries(_dict
					.getEntries());

			ArrayList<Entry> entry_list = new ArrayList<Entry>();
			for (Entry entry : entries) {
				if (entry.getOrthography().equals(text)) {
					// Put exact matches to the beginning of the list
					entry_list.add(0, entry);
				} else {
					entry_list.add(entry);
				}
			}
			_selected_senses_tree.setEntries(entry_list.toArray(new Entry[0]));
		}
	}

	private void updateActions() {
		boolean element_selected = _current_senses_table.getSelectedObjects()
				.size() > 0;
		_remove_sense_action.setEnabled(element_selected);
		_add_sense_action
				.setEnabled(_selected_senses_tree.getSelectedObject() != null);
	}

	private void updateStatusLabels() {
		// -----
		// Update _current_senses_label
		Example.TextFragment tf = _current_senses_table
				.getSelectedTextFragment();
		if (tf == null) {
			_current_senses_label.setText(" ");
		} else {
			Collection<Example> examples = _dict.getExamples(tf.getSense());
			int num = examples.size();
			// "example" is the original example, or "null", if a new example
			// is created in this dialog. "_example" is the cloned
			// or the new example.
			Example example = _dict.getExample(_example.getID());
			if (example == null) {
				num++;
			} else if (!Utils.arrayContainsItem(example.getSenses(), tf
					.getSense())) {
				num++;
			}

			_current_senses_label.setText(I18nService.getString("Labels",
					"num_linked_examples", new Object[] { num }));
		}

		// -----
		// Update _available_senses_label
		Sense sense = _selected_senses_tree.getSelectedSense();
		if (sense == null) {
			_available_senses_label.setText(" ");
		} else {
			Collection<Example> examples = _dict.getExamples(sense);
			int num = examples.size();
			Example example = _dict.getExample(_example.getID());
			if (example == null) {
				if (Utils.arrayContainsItem(_example.getSenses(), sense)) {
					num++;
				}
			} else if (Utils.arrayContainsItem(_example.getSenses(), sense)
					&& !Utils.arrayContainsItem(example.getSenses(), sense)) {
				num++;
			} else if (Utils.arrayContainsItem(example.getSenses(), sense)
					&& !Utils.arrayContainsItem(_example.getSenses(), sense)) {
				num--;
			}

			_available_senses_label.setText(I18nService.getString("Labels",
					"num_linked_examples", new Object[] { num }));
		}
	}
}

class ExampleTextField extends JTextArea {
	private static final long serialVersionUID = 1L;

	private Example _example;

	public ExampleTextField() {
		super();
		_example = null;

		Font f = ((UIConfig) JVLT.getConfig()).getFontProperty("ui_orth_font");
		if (f != null) {
			setFont(f);
		}
	}

	@Override
	protected Document createDefaultModel() {
		return new ExampleDocument();
	}

	public Example getExample() {
		return _example;
	}

	public void setExample(Example example) {
		_example = example;
		ExampleDocument doc = (ExampleDocument) getDocument();
		doc.setExample(null);
		setText(example.getText());
		doc.setExample(example);
	}
}

class ExampleDocument extends PlainDocument {
	private static final long serialVersionUID = 1L;

	private Example _example;

	public ExampleDocument() {
		super();
		_example = null;
	}

	@Override
	public void insertString(int offs, String str, AttributeSet a)
			throws BadLocationException {
		if (_example == null) {
			super.insertString(offs, str, a);
			return;
		}

		Example.TextFragment[] fragments = _example.getTextFragments();
		Example.TextFragment fragment = null;
		int insert_offset = -1;

		if (fragments.length == 0) {
			fragment = new Example.TextFragment(str);
			_example.addTextFragment(fragment);
			insert_offset = -1;
		} else {
			int tf_offset = 0;
			for (int i = 0; i < fragments.length; i++) {
				Example.TextFragment tf = fragments[i];
				int len = tf.getText().length();
				if (tf_offset < offs && offs < tf_offset + len) {
					// Index is located in the middle of a text fragment
					// with a sense - no change possible.
					if (tf.getSense() != null) {
						return;
					}
					fragment = tf;
					insert_offset = offs - tf_offset;
					break;
				} else if (tf_offset == offs) {
					// Index is located at the beginning of a text fragment.
					// If this text fragment is not associated with a sense
					// there is no problem. Otherwise try the previous
					// fragment or create a new one.
					if (tf.getSense() == null) {
						fragment = tf;
						insert_offset = 0;
						break;
					} else if (i > 0 && fragments[i - 1].getSense() == null) {
						fragment = fragments[i - 1];
						insert_offset = fragments[i - 1].getText().length();
						break;
					} else {
						fragment = new Example.TextFragment(str);
						_example.insertTextFragmentBefore(fragment, tf);
						insert_offset = -1; // do not modify fragment
						break;
					}
				} else if (offs == tf_offset + len) {
					// Index is located at the end of a text fragment.
					if (tf.getSense() == null) {
						fragment = tf;
						insert_offset = len;
						break;
					} else if (i < fragments.length - 1
							&& fragments[i + 1].getSense() == null) {
						fragment = fragments[i + 1];
						insert_offset = 0;
						break;
					} else {
						fragment = new Example.TextFragment(str);
						_example.insertTextFragmentAfter(fragment, tf);
						insert_offset = -1; // do not modify fragment
						break;
					}
				}

				tf_offset += len;
			} // for (int i=0; i<fragments.length; i++)

			if (insert_offset >= 0) {
				String new_tf_text = Utils.insertString(fragment.getText(),
						insert_offset, str);
				fragment.setText(new_tf_text);
			}
		}

		// System.out.println(fragment.getText());
		super.insertString(offs, str, a);
	}

	@Override
	public void remove(int offs, int len) throws BadLocationException {
		if (_example != null) {
			Example.TextFragment[] fragments = _example.getTextFragments();
			int first_index = offs;
			int last_index = offs + len - 1;
			int tf_first = 0;
			for (TextFragment tf : fragments) {
				String tf_str = tf.getText();
				int tf_last = tf_first + tf_str.length() - 1;
				if ((tf_first <= first_index && first_index <= tf_last)
						|| (tf_first >= first_index && last_index >= tf_first)) {
					if (tf.getSense() != null) {
						// Fragment cannot be removed because there is a link.
						return;
					}
				}

				tf_first += tf_str.length();
			}

			tf_first = 0;
			for (TextFragment tf : fragments) {
				String tf_str = tf.getText();
				int tf_last = tf_first + tf_str.length() - 1;
				int delete_first = -1;
				int delete_last = -1;
				if (tf_first <= first_index && first_index <= tf_last) {
					delete_first = first_index - tf_first;
					delete_last = last_index <= tf_last ? last_index - tf_first
							: tf_last - tf_first;
				} else if (tf_first >= first_index && last_index >= tf_first) {
					delete_first = 0;
					delete_last = last_index <= tf_last ? last_index - tf_first
							: tf_last - tf_first;
				}

				if (delete_first >= 0) {
					if (delete_first == tf_first && delete_last == tf_last) {
						_example.removeTextFragment(tf);
					} else {
						tf.setText(Utils.removeSubstring(tf_str, delete_first,
								delete_last));
					}
				}

				tf_first += tf_str.length();
			}
		}

		super.remove(offs, len);
	}

	public void setExample(Example example) {
		_example = example;
	}
}
