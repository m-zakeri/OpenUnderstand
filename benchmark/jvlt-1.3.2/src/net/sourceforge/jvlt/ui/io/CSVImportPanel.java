package net.sourceforge.jvlt.ui.io;

import java.awt.Component;
import java.awt.GridBagLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import java.util.TreeSet;
import java.util.Vector;

import javax.swing.AbstractCellEditor;
import javax.swing.DefaultCellEditor;
import javax.swing.JCheckBox;
import javax.swing.JComboBox;
import javax.swing.JScrollPane;
import javax.swing.JSpinner;
import javax.swing.JTable;
import javax.swing.SpinnerNumberModel;
import javax.swing.border.EtchedBorder;
import javax.swing.border.TitledBorder;
import javax.swing.event.ChangeEvent;
import javax.swing.event.ChangeListener;
import javax.swing.event.TableModelEvent;
import javax.swing.event.TableModelListener;
import javax.swing.table.AbstractTableModel;
import javax.swing.table.TableCellEditor;
import javax.xml.xpath.XPathExpressionException;

import net.sourceforge.jvlt.JVLT;
import net.sourceforge.jvlt.core.ArraySchemaAttribute;
import net.sourceforge.jvlt.core.EntryAttributeSchema;
import net.sourceforge.jvlt.core.EntryClass;
import net.sourceforge.jvlt.core.SchemaAttribute;
import net.sourceforge.jvlt.io.EntryAttributeSchemaReader;
import net.sourceforge.jvlt.ui.components.LabeledSpinner;
import net.sourceforge.jvlt.ui.components.LanguageComboBox;
import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.utils.AttributeResources;
import net.sourceforge.jvlt.utils.Config;
import net.sourceforge.jvlt.utils.I18nService;
import net.sourceforge.jvlt.utils.Utils;

import org.apache.log4j.Logger;

public class CSVImportPanel extends CSVPanel {
	private static final Logger logger = Logger.getLogger(CSVImportPanel.class);

	private class ActionHandler implements ActionListener {
		public void actionPerformed(ActionEvent ev) {
			if (ev.getSource() == _language_box) {
				updateAttributePanel();
			}

			_preview_model.update();
		}
	}

	private class ChangeHandler implements ChangeListener {
		public void stateChanged(ChangeEvent ev) {
			_preview_model.update();
		}
	}

	private class TableModelHandler implements TableModelListener {
		public void tableChanged(TableModelEvent ev) {
			_preview_model.update();
		}
	}

	private class PreviewTableModel extends AbstractTableModel {
		private static final long serialVersionUID = 1L;

		private final AttributeResources _resources = new AttributeResources();
		private String[] _column_names = new String[0];

		public int getRowCount() {
			return _column_names.length;
		}

		public int getColumnCount() {
			return 2;
		}

		public Object getValueAt(int row, int column) {
			if (column == 0) {
				return "" + (row + 1) + ".";
			}
			return _column_names[row];
		}

		@Override
		public String getColumnName(int column) {
			if (column == 0) {
				return "";
			}
			return I18nService.getString("Labels", "column_name");
		}

		public void update() {
			_column_names = getColumnNames();
			fireTableDataChanged();
		}

		private String[] getColumnNames() {
			ArrayList<String> names = new ArrayList<String>();
			int num_senses = _num_senses_spinner_model.getNumber().intValue();
			int num_categories = _num_categories_spinner_model.getNumber()
					.intValue();
			int num_mmfiles = _num_multimedia_files_spinner_model.getNumber()
					.intValue();
			int num_examples = _num_examples_spinner_model.getNumber()
					.intValue();
			AttributeTable.AttributeTableModel tablemodel = (AttributeTable.AttributeTableModel) _attribute_table
					.getModel();
			SchemaAttribute[] attributes = tablemodel.getSelectedAttributes();

			names.add(_resources.getString("Orthography"));
			names.add(_resources.getString("Pronunciations"));
			for (int i = 0; i < num_senses; i++) {
				names.add(getTranslation("nth_translation", i + 1));
				names.add(getTranslation("nth_definition", i + 1));
			}
			names.add(_resources.getString("Lesson"));
			for (int i = 0; i < num_categories; i++) {
				names.add(getTranslation("nth_category", i + 1));
			}
			for (int i = 0; i < num_mmfiles; i++) {
				names.add(getTranslation("nth_mmfile", i + 1));
			}
			for (int i = 0; i < num_examples; i++) {
				names.add(getTranslation("nth_example", i + 1));
				names.add(getTranslation("nth_example_link", i + 1));
				names.add(getTranslation("nth_example_translation", i + 1));
			}
			if (CSVImportPanel.this._language_box.getSelectedLanguage() != null) {
				names.add(_resources.getString("EntryClass"));
			}
			for (SchemaAttribute attr : attributes) {
				String translation = _resources.getString(attr.getName());
				int columns = tablemodel.getNumColumns(attr);
				if (columns == 1) {
					names.add(translation);
				} else {
					for (int j = 0; j < columns; j++) {
						names.add(I18nService.getString("Labels",
								"nth_attribute_column", new Object[] {
										translation, j + 1 }));
					}
				}
			}

			return names.toArray(new String[0]);
		}

		private String getTranslation(String key, int argument) {
			return I18nService.getString("Labels", key, new Object[] { argument });
		}
	}

	private static final long serialVersionUID = 1L;

	private LanguageComboBox _language_box;
	private SpinnerNumberModel _num_senses_spinner_model;
	private SpinnerNumberModel _num_categories_spinner_model;
	private SpinnerNumberModel _num_multimedia_files_spinner_model;
	private SpinnerNumberModel _num_examples_spinner_model;
	private LabeledSpinner _num_senses_spinner;
	private LabeledSpinner _num_categories_spinner;
	private LabeledSpinner _num_multimedia_files_spinner;
	private LabeledSpinner _num_examples_spinner;
	private JCheckBox _ignore_first_row_box;
	private AttributeTable _attribute_table;
	private JScrollPane _attribute_pane;
	private PreviewTableModel _preview_model;
	private JScrollPane _preview_pane;

	@Override
	protected void initComponents() {
		super.initComponents();

		ChangeHandler ch = new ChangeHandler();
		ActionHandler ah = new ActionHandler();
		TableModelHandler tmh = new TableModelHandler();

		_language_box = new LanguageComboBox();
		_language_box.addActionListener(ah);

		_num_senses_spinner_model = createSpinnerModel();
		_num_senses_spinner_model.setValue(1);
		_num_senses_spinner = new LabeledSpinner(_num_senses_spinner_model);
		_num_senses_spinner.setLabel("num_senses");
		_num_senses_spinner.addChangeListener(ch);

		_num_categories_spinner_model = createSpinnerModel();
		_num_categories_spinner = new LabeledSpinner(
				_num_categories_spinner_model);
		_num_categories_spinner.setLabel("num_categories");
		_num_categories_spinner.addChangeListener(ch);

		_num_multimedia_files_spinner_model = createSpinnerModel();
		_num_multimedia_files_spinner = new LabeledSpinner(
				_num_multimedia_files_spinner_model);
		_num_multimedia_files_spinner.setLabel("num_multimedia_files");
		_num_multimedia_files_spinner.addChangeListener(ch);

		_num_examples_spinner_model = createSpinnerModel();
		_num_examples_spinner = new LabeledSpinner(_num_examples_spinner_model);
		_num_examples_spinner.setLabel("num_examples");
		_num_examples_spinner.addChangeListener(ch);

		_ignore_first_row_box = new JCheckBox(I18nService.getString("Actions",
				"ignore_first_row"));
		_ignore_first_row_box.addActionListener(ah);

		_attribute_table = new AttributeTable();
		_attribute_table.getModel().addTableModelListener(tmh);
		_attribute_pane = new JScrollPane(_attribute_table);
		_attribute_pane.setBorder(new TitledBorder(new EtchedBorder(
				EtchedBorder.LOWERED), I18nService.getString("Labels",
				"attributes")));

		_preview_model = new PreviewTableModel();
		_preview_model.update();
		JTable preview_table = new JTable(_preview_model);
		preview_table.setRowHeight(preview_table.getFontMetrics(
				preview_table.getFont()).getHeight());
		preview_table.setAutoResizeMode(JTable.AUTO_RESIZE_ALL_COLUMNS);
		preview_table.getColumnModel().getColumn(0).setPreferredWidth(10);
		_preview_pane = new JScrollPane(preview_table);
		_preview_pane.setBorder(new TitledBorder(new EtchedBorder(
				EtchedBorder.LOWERED), I18nService.getString("Labels",
				"csv_columns")));
	}

	public String getLanguage() {
		return _language_box.getSelectedLanguage();
	}

	public int getNumSenses() {
		return _num_senses_spinner_model.getNumber().intValue();
	}

	public int getNumCategories() {
		return _num_categories_spinner_model.getNumber().intValue();
	}

	public int getNumExamples() {
		return _num_examples_spinner_model.getNumber().intValue();
	}

	public int getNumMultimediaFiles() {
		return _num_multimedia_files_spinner_model.getNumber().intValue();
	}

	public boolean getIgnoreFirstRow() {
		return _ignore_first_row_box.isSelected();
	}

	public SchemaAttribute[] getAttributes() {
		AttributeTable.AttributeTableModel model = (AttributeTable.AttributeTableModel) _attribute_table
				.getModel();
		return model.getSelectedAttributes();
	}

	public int[] getAttributeColumns() {
		AttributeTable.AttributeTableModel model = (AttributeTable.AttributeTableModel) _attribute_table
				.getModel();
		SchemaAttribute[] attrs = getAttributes();
		int[] columns = new int[attrs.length];
		for (int i = 0; i < attrs.length; i++) {
			columns[i] = model.getNumColumns(attrs[i]);
		}

		return columns;
	}

	public void loadState() {
		Config config = JVLT.getConfig();
		String language = config.getProperty("CSVImport.Language", "");
		_language_box.setSelectedLanguage(language);
		_text_delim_box.setSelectedItem(config.getProperty(
				"CSVImport.TextDelimiter", "\""));
		_field_delim_box.setSelectedItem(config.getProperty(
				"CSVImport.FieldDelimiter", ","));
		_charset_box.setSelectedItem(config.getProperty("CSVImport.Charset",
				"UTF-8"));
		_num_senses_spinner_model.setValue(config.getIntProperty(
				"CSVImport.NumSenses", 1));
		_num_categories_spinner_model.setValue(config.getIntProperty(
				"CSVImport.NumCategories", 0));
		_num_multimedia_files_spinner_model.setValue(config.getIntProperty(
				"CSVImport.NumMultimediaFiles", 0));
		_num_examples_spinner_model.setValue(config.getIntProperty(
				"CSVImport.NumExamples", 0));
		_ignore_first_row_box.setSelected(config.getBooleanProperty(
				"CSVImport.IgnoreFirstRow", false));
		String attr_string = config.getProperty("CSVImport.Attributes", "");
		String[] attr_strings = Utils.split(attr_string);
		ArrayList<SchemaAttribute> attrs = new ArrayList<SchemaAttribute>();
		ArrayList<Integer> columns = new ArrayList<Integer>();
		SchemaAttribute[] available_attrs = new SchemaAttribute[0];
		if (!language.equals("")) {
			available_attrs = getSchemaAttributes(language);
		}

		try {
			for (int i = 0; i < attr_strings.length / 2; i++) {
				for (SchemaAttribute availableAttr : available_attrs) {
					if (availableAttr.getName().equals(attr_strings[2 * i])) {
						attrs.add(availableAttr);
						break;
					}
				}
				columns.add(Integer.parseInt(attr_strings[2 * i + 1]));
			}

			if (attrs.size() == columns.size()) {
				_attribute_table.setSelectedAttributes(attrs, columns);
			}
		} catch (NumberFormatException e) {
			logger.error(e);
		}
	}

	public void saveState() {
		Config config = JVLT.getConfig();
		if (getLanguage() != null) {
			config.setProperty("CSVImport.Language", getLanguage());
		}
		config.setProperty("CSVImport.TextDelimiter", String
				.valueOf(getTextDelimiter()));
		config.setProperty("CSVImport.FieldDelimiter", String
				.valueOf(getFieldDelimiter()));
		config.setProperty("CSVImport.Charset", String.valueOf(getCharset()));
		config.setProperty("CSVImport.NumSenses", String
				.valueOf(getNumSenses()));
		config.setProperty("CSVImport.NumCategories", String
				.valueOf(getNumCategories()));
		config.setProperty("CSVImport.NumMultimediaFiles", String
				.valueOf(getNumMultimediaFiles()));
		config.setProperty("CSVImport.NumExamples", String
				.valueOf(getNumExamples()));
		config.setProperty("CSVImport.IgnoreFirstRow", String
				.valueOf(getIgnoreFirstRow()));
		SchemaAttribute[] attrs = getAttributes();
		int[] attr_columns = getAttributeColumns();
		StringBuffer buf = new StringBuffer();
		for (int i = 0; i < attrs.length; i++) {
			if (i > 0) {
				buf.append(';');
			}
			buf.append(attrs[i].getName());
			buf.append(';');
			buf.append(attr_columns[i]);
		}
		config.setProperty("CSVImport.Attributes", buf.toString());
	}

	@Override
	protected void initLayout() {
		setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1.0, 0.0);
		add(_text_delim_box.getLabel(), cc);
		cc.update(1, 0, 1.0, 0.0);
		add(_text_delim_box, cc);
		cc.update(0, 1, 1.0, 0.0);
		add(_field_delim_box.getLabel(), cc);
		cc.update(1, 1, 1.0, 0.0);
		add(_field_delim_box, cc);
		cc.update(0, 2, 1.0, 0.0);
		add(_charset_box.getLabel(), cc);
		cc.update(1, 2, 1.0, 0.0);
		add(_charset_box, cc);
		cc.update(0, 3, 1.0, 0.0);
		add(_language_box.getLabel(), cc);
		cc.update(1, 3, 1.0, 0.0);
		add(_language_box, cc);
		cc.update(2, 0, 1.0, 0.0);
		add(_num_senses_spinner.getLabel(), cc);
		cc.update(3, 0, 1.0, 0.0);
		add(_num_senses_spinner, cc);
		cc.update(2, 1, 1.0, 0.0);
		add(_num_categories_spinner.getLabel(), cc);
		cc.update(3, 1, 1.0, 0.0);
		add(_num_categories_spinner, cc);
		cc.update(2, 2, 1.0, 0.0);
		add(_num_multimedia_files_spinner.getLabel(), cc);
		cc.update(3, 2, 1.0, 0.0);
		add(_num_multimedia_files_spinner, cc);
		cc.update(2, 3, 1.0, 0.0);
		add(_num_examples_spinner.getLabel(), cc);
		cc.update(3, 3, 1.0, 0.0);
		add(_num_examples_spinner, cc);
		cc.update(0, 4, 1.0, 0.0, 4, 1);
		add(_ignore_first_row_box, cc);
		cc.update(0, 5, 1.0, 1.0, 2, 1);
		add(_attribute_pane, cc);
		cc.update(2, 5, 1.0, 1.0, 2, 1);
		add(_preview_pane, cc);
	}

	private SpinnerNumberModel createSpinnerModel() {
		SpinnerNumberModel model = new SpinnerNumberModel();
		model.setStepSize(1);
		model.setMinimum(0);
		model.setMaximum(10);
		model.setValue(0);
		return model;
	}

	private void updateAttributePanel() {
		String language = _language_box.getSelectedLanguage();
		if (language != null) {
			_attribute_table
					.setAvailableAttributes(getSchemaAttributes(language));
		}
	}

	private SchemaAttribute[] getSchemaAttributes(String language) {
		EntryAttributeSchemaReader reader = new EntryAttributeSchemaReader();
		try {
			EntryAttributeSchema schema = reader.readSchema(language);
			EntryClass[] classes = schema.getEntryClasses();
			TreeSet<SchemaAttribute> attrs = new TreeSet<SchemaAttribute>();
			for (EntryClass classe : classes) {
				attrs.addAll(Arrays.asList(classe.getAttributes()));
			}

			return attrs.toArray(new SchemaAttribute[0]);
		} catch (XPathExpressionException ex) {
			return new SchemaAttribute[0];
		}
	}
}

class AttributeTable extends JTable {
	public static class AttributeTableModel extends AbstractTableModel {
		private static final long serialVersionUID = 1L;

		private final AttributeResources _resources = new AttributeResources();
		private final Map<String, SchemaAttribute> _translation_attr_map;
		private final Vector<Object> _attributes;
		private final Vector<Object> _num_columns;

		public AttributeTableModel() {
			_translation_attr_map = new HashMap<String, SchemaAttribute>();
			_attributes = new Vector<Object>();
			_num_columns = new Vector<Object>();
		}

		public int getRowCount() {
			return _attributes.size() + 1;
		}

		public int getColumnCount() {
			return 2;
		}

		public Object getValueAt(int row, int column) {
			if (row == _attributes.size()) {
				return null;
			}
			if (column == 0) {
				return _attributes.get(row);
			}
			Object val = _num_columns.get(row);
			return val == null ? 1 : val;
		}

		@Override
		public boolean isCellEditable(int row, int column) {
			if (column == 0) {
				return true;
			}
			return (getAttributeAt(row) instanceof ArraySchemaAttribute);
		}

		@Override
		public Class<? extends Object> getColumnClass(int column) {
			if (column == 0) {
				return String.class;
			}
			return Integer.class;
		}

		@Override
		public void setValueAt(Object value, int row, int column) {
			if (row >= _attributes.size()) {
				if (value != null && !value.equals("")) {
					_attributes.setSize(row + 1);
					_num_columns.setSize(row + 1);
					if (column == 0) {
						_attributes.set(row, value);
					} else {
						_num_columns.set(row, value);
					}
					fireTableRowsUpdated(row, row);
					fireTableRowsInserted(row + 1, row + 1);
				}
			} else {
				if (column == 0) {
					SchemaAttribute attr = _translation_attr_map.get(value);
					if (attr == null) {
						for (int i = row; i < _attributes.size() - 1; i++) {
							_attributes.set(i, _attributes.get(i + 1));
						}
						_attributes.setSize(_attributes.size() - 1);
						fireTableRowsDeleted(row, row);
					} else {
						_attributes.set(row, value);
						fireTableRowsUpdated(row, row);
					}
				} else {
					_num_columns.set(row, value);
					fireTableCellUpdated(row, column);
				}
			}
		}

		@Override
		public String getColumnName(int column) {
			if (column == 0) {
				return I18nService.getString("Labels", "attribute");
			}
			return I18nService.getString("Labels", "num_columns");
		}

		public void clear() {
			int size = _attributes.size();
			_attributes.clear();
			_num_columns.clear();
			fireTableRowsDeleted(0, size - 1);
		}

		public void setAvailableAttributes(SchemaAttribute[] attrs) {
			_translation_attr_map.clear();
			for (SchemaAttribute attr : attrs) {
				_translation_attr_map.put(_resources.getString(attr.getName()),
						attr);
			}
		}

		public SchemaAttribute[] getSelectedAttributes() {
			ArrayList<SchemaAttribute> list = new ArrayList<SchemaAttribute>();
			for (int i = 0; i < _attributes.size(); i++) {
				list.add(_translation_attr_map.get(_attributes.get(i)));
			}

			return list.toArray(new SchemaAttribute[0]);
		}

		public int getNumColumns(SchemaAttribute attr) {
			String trans = _resources.getString(attr.getName());
			for (int i = 0; i < _attributes.size(); i++) {
				if (_attributes.get(i).equals(trans)) {
					Object val = _num_columns.get(i);
					return val == null ? 1 : ((Integer) val).intValue();
				}
			}

			return 0;
		}

		public void setSelectedAttributes(Collection<SchemaAttribute> attrs,
				Collection<Integer> columns) {
			_attributes.clear();
			_num_columns.clear();
			Iterator<SchemaAttribute> attr_it = attrs.iterator();
			Iterator<Integer> col_it = columns.iterator();
			while (attr_it.hasNext() && col_it.hasNext()) {
				_attributes.add(_resources.getString(attr_it.next().getName()));
				_num_columns.add(col_it.next());
			}
			fireTableDataChanged();
		}

		private SchemaAttribute getAttributeAt(int row) {
			String val = null;
			if (row < _attributes.size()) {
				val = (String) _attributes.get(row);
			}

			if (val == null || val.equals("")) {
				return null;
			}
			return _translation_attr_map.get(val);
		}
	}

	private static final long serialVersionUID = 1L;

	private final JComboBox _attribute_box;

	public AttributeTable() {
		super(new AttributeTableModel());

		_attribute_box = new JComboBox();
		getColumnModel().getColumn(0).setCellEditor(
				new DefaultCellEditor(_attribute_box));
		getColumnModel().getColumn(1).setCellEditor(new SpinnerEditor());
		setRowHeight(getFontMetrics(getFont()).getHeight());
	}

	public void setAvailableAttributes(SchemaAttribute[] attrs) {
		AttributeResources resources = new AttributeResources();
		AttributeTableModel model = (AttributeTableModel) getModel();

		model.clear();
		model.setAvailableAttributes(attrs);
		_attribute_box.removeAllItems();
		_attribute_box.addItem("");
		for (SchemaAttribute attr : attrs) {
			_attribute_box.addItem(resources.getString(attr.getName()));
		}
	}

	public void setSelectedAttributes(Collection<SchemaAttribute> attrs,
			Collection<Integer> columns) {
		AttributeTableModel atm = (AttributeTableModel) getModel();
		atm.setSelectedAttributes(attrs, columns);
	}
}

class SpinnerEditor extends AbstractCellEditor implements TableCellEditor {
	private static final long serialVersionUID = 1L;

	private final JSpinner _spinner = new JSpinner();

	public SpinnerEditor() {
		SpinnerNumberModel model = new SpinnerNumberModel();
		model.setStepSize(1);
		model.setMinimum(0);
		model.setMaximum(10);
		_spinner.setModel(model);
	}

	public Component getTableCellEditorComponent(JTable table, Object value,
			boolean isSelected, int row, int column) {
		_spinner.setValue(value);
		return _spinner;
	}

	public Object getCellEditorValue() {
		return _spinner.getValue();
	}
}
