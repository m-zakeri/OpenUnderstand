package net.sourceforge.jvlt.ui.table;

import java.text.Collator;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;

import javax.swing.event.TableModelEvent;
import javax.swing.event.TableModelListener;
import javax.swing.table.TableModel;

import net.sourceforge.jvlt.metadata.Attribute;
import net.sourceforge.jvlt.metadata.MetaData;
import net.sourceforge.jvlt.utils.AttributeResources;
import net.sourceforge.jvlt.utils.CustomCollator;

import org.apache.log4j.Logger;

public class SortableTableModel<T extends Object> implements TableModel {

	private static final Logger logger = Logger
			.getLogger(SortableTableModel.class);

	/**
	 * Sort order options of table columns.
	 * 
	 * @author thrar
	 */
	public enum SortOrder {
		/** Descending sort (high values first) */
		DESCENDING(-1),
		/** Ascending sort (low values first) */
		ASCENDING(1),
		/** No defined sort order */
		NOT_SORTED(0);

		private final int intValue;

		private SortOrder(int intValue) {
			this.intValue = intValue;
		}

		/**
		 * Checks if this value represents a sorted order.
		 * 
		 * @return <tt>true</tt> if this value represents a sorted order
		 */
		public boolean isSorted() {
			return this != NOT_SORTED;
		}

		/**
		 * Converts this order to int.
		 * 
		 * @return the int value representing this order
		 */
		public int toInt() {
			return intValue;
		}

		/**
		 * Returns the sort order for the given numerical value.
		 * 
		 * @param intValue the value for which to find the corresponding sort
		 * @return the sort order for the given numerical value, or
		 *         {@link #NOT_SORTED} if no such order exists
		 */
		public static SortOrder valueOf(int intValue) {
			for (SortOrder order : values()) {
				if (order.intValue == intValue) {
					return order;
				}
			}
			return NOT_SORTED;
		}
	}

	private List<Row> _view_to_model;
	private int[] _model_to_view;
	private final AttributeResources _resources;
	private final ArrayList<TableModelListener> _listeners;
	private final ArrayList<String> _columns;
	private final ArrayList<T> _values;
	private Directive _directive;
	private final MetaData _data;
	private final Map<Class<? extends Attribute>, Boolean> _format_value;

	public SortableTableModel(MetaData data) {
		_resources = new AttributeResources();
		_listeners = new ArrayList<TableModelListener>();
		_columns = new ArrayList<String>();
		_values = new ArrayList<T>();
		_directive = new Directive(-1, SortOrder.NOT_SORTED);
		_data = data;
		_view_to_model = null;
		_model_to_view = null;
		_format_value = new HashMap<Class<? extends Attribute>, Boolean>();
	}

	/** Implementation of TableModel.addTableModelListener(). */
	public void addTableModelListener(TableModelListener l) {
		_listeners.add(l);
	}

	/** Implementation of TableModel.getColumnClass(). */
	public Class<? extends Object> getColumnClass(int col) {
		Attribute attr = _data.getAttribute(_columns.get(col).toString());
		if (_format_value.containsKey(attr.getClass())) {
			return String.class;
		}
		return _data.getAttribute(_columns.get(col).toString()).getType();
	}

	/** Implementation of TableModel.getColumnCount(). */
	public int getColumnCount() {
		return _columns.size();
	}

	/** Implements TableModel.getColumnName(). */
	public String getColumnName(int col) {
		String name = _columns.get(col).toString();
		return _resources.getString(name);
	}

	/** Implementation of TableModel.getRowCount(). */
	public int getRowCount() {
		return _values.size();
	}

	/** Implementation of TableModel.getValueAt(). */
	public Object getValueAt(int row, int col) {
		return getValue(getModelIndex(row), col);
	}

	/** Implementation of TableModel.isCellEditable(). */
	public boolean isCellEditable(int row, int col) {
		return false;
	}

	/** Implementation of TableModel.removeTableModelListener(). */
	public void removeTableModelListener(TableModelListener l) {
		_listeners.remove(l);
	}

	/** Implementation of TableModel.setValueAt() (does nothing). */
	public void setValueAt(Object val, int row, int col) {
		// not editable, do nothing
	}

	public Directive getSortingDirective() {
		return _directive;
	}

	/**
	 * Sets the sorting directive. If the column of the directive is invalid, an
	 * empty directive (no sorting) is chosen.
	 */
	public void setSortingDirective(Directive directive) {
		if (directive.getColumn() >= getColumnCount()
				|| directive.getColumn() < 0) {
			_directive = new Directive();
		} else {
			_directive = directive;
		}

		clearSortingState();
		fireTableModelEvent(new TableModelEvent(this));
		fireTableModelEvent(new TableModelEvent(this,
				TableModelEvent.HEADER_ROW));
	}

	/** Set column names (not translated version). */
	public void setColumnNames(String[] names) {
		_columns.clear();
		for (String name : names) {
			if (_data.getAttribute(name) != null) {
				_columns.add(name);
			}
		}

		// Number of columns may change, so the current sorting directive
		// is possibly invalid. Correct this by calling setSortingDirective().
		setSortingDirective(_directive);
		fireTableModelEvent(new TableModelEvent(this,
				TableModelEvent.HEADER_ROW));
	}

	/** Returns the name of a column (either translated or not translated) */
	public String getColumnName(int column, boolean translate) {
		if (translate) {
			return getColumnName(column);
		}
		return _columns.get(column).toString();
	}

	/** Return the column names (not translated version). */
	public String[] getColumnNames() {
		return _columns.toArray(new String[0]);
	}

	public MetaData getMetaData() {
		return _data;
	}

	public boolean containsObject(Object obj) {
		return _values.contains(obj);
	}

	public Collection<T> getObjects() {
		return _values;
	}

	public T getObjectAt(int row) {
		return _values.get(getModelIndex(row));
	}

	public int getObjectIndex(T obj) {
		int index = 0;
		Iterator<T> it = _values.iterator();
		while (it.hasNext()) {
			T o = it.next();
			if (o.equals(obj)) {
				return getViewIndex(index);
			}
			index++;
		}

		return -1;
	}

	public void addObject(T obj) {
		_values.add(obj);
		clearSortingState();
		fireTableModelEvent(new TableModelEvent(this));
		// int row = _values.size()-1;
		// fireTableModelEvent(new TableModelEvent(this, row, row,
		// TableModelEvent.ALL_COLUMNS, TableModelEvent.INSERT));
	}

	public void addObjects(Collection<T> objs) {
		_values.addAll(objs);
		if (objs.size() > 0) {
			clearSortingState();
			fireTableModelEvent(new TableModelEvent(this));
		}
	}

	public void clear() {
		_values.clear();
		clearSortingState();
		fireTableModelEvent(new TableModelEvent(this));
	}

	public void setObjects(Collection<T> objects) {
		clear();
		addObjects(objects);
	}

	public void removeObject(T obj) {
		int row = getObjectIndex(obj);
		if (row < 0) {
			return;
		}

		_values.remove(obj);
		clearSortingState();
		fireTableModelEvent(new TableModelEvent(this));
		// fireTableModelEvent(new TableModelEvent(this, row, row,
		// TableModelEvent.ALL_COLUMNS, TableModelEvent.DELETE));
	}

	public void updateObjects(T[] objects) {
		boolean exists_visible_object = false;
		for (T object : objects) {
			if (getObjectIndex(object) >= 0) {
				exists_visible_object = true;
				break;
			}
		}

		if (!exists_visible_object) {
			return;
		}

		clearSortingState();
		fireTableModelEvent(new TableModelEvent(this));
		// fireTableModelEvent(new TableModelEvent(this, row, row,
		// TableModelEvent.ALL_COLUMNS, TableModelEvent.UPDATE));
	}

	public void setFormatValue(Class<? extends Attribute> cl, boolean format) {
		_format_value.put(cl, format);
	}

	private void clearSortingState() {
		_view_to_model = null;
		_model_to_view = null;
	}

	Object getValue(int row, int col) {
		Object obj = _values.get(row);
		Attribute attr = _data.getAttribute(_columns.get(col).toString());
		if (_format_value.containsKey(attr.getClass())) {
			return attr.getFormattedValue(obj);
		}

		if (Number.class.isAssignableFrom(attr.getType())
				|| Boolean.class.isAssignableFrom(attr.getType())) {
			/*
			 * For numbers and booleans use the native type, so the appropriate
			 * cell renderers can be used
			 */
			return attr.getValue(obj);
		}

		return attr.getFormattedValue(obj);
	}

	private int getModelIndex(int row) {
		return getViewToModel().get(row).getIndex();
	}

	private List<Row> getViewToModel() {
		if (_view_to_model == null) {
			int row_count = getRowCount();
			_view_to_model = new ArrayList<Row>();
			for (int row = 0; row < row_count; row++) {
				_view_to_model.add(new Row(row));
			}

			if (_directive.getDirection().isSorted()) {
				Collections.sort(_view_to_model);
			}
		}

		return _view_to_model;
	}

	private int getViewIndex(int row) {
		return getModelToView()[row];
	}

	private int[] getModelToView() {
		if (_model_to_view == null) {
			int n = getViewToModel().size();
			_model_to_view = new int[n];
			for (int i = 0; i < n; i++) {
				_model_to_view[getModelIndex(i)] = i;
			}
		}

		return _model_to_view;
	}

	private void fireTableModelEvent(TableModelEvent ev) {
		Iterator<TableModelListener> it = _listeners.iterator();
		while (it.hasNext()) {
			it.next().tableChanged(ev);
		}
	}

	public static class Directive {
		private int _column;
		private SortOrder _direction;

		public Directive() {
			this(-1, SortOrder.NOT_SORTED);
		}

		public Directive(int column, SortOrder direction) {
			_column = column;
			_direction = direction;
		}

		public int getColumn() {
			return _column;
		}

		public SortOrder getDirection() {
			return _direction;
		}

		public void setColumn(int col) {
			_column = col;
		}

		public void setDirection(SortOrder dir) {
			_direction = dir;
		}
	}

	class Row implements Comparable<Row> {
		private final int _index;
		private final Collator _collator;

		public Row(int index) {
			_index = index;

			_collator = CustomCollator.getInstance();
		}

		public int getIndex() {
			return _index;
		}

		public int compareTo(Row r) {
			int row1 = _index;
			int row2 = r._index;
			int col = _directive.getColumn();
			if (col < 0) {
				return 0;
			}

			SortOrder direction = _directive.getDirection();
			Object val1 = getValue(row1, col);
			Object val2 = getValue(row2, col);

			int comparison = 0;
			if (val1 == null && val2 == null) {
				comparison = 0;
			} else if (val1 == null) {
				comparison = -1;
			} else if (val2 == null) {
				comparison = 1;
			} else {
				if (val1 instanceof String && val2 instanceof String) {
					comparison = _collator.compare(val1, val2);
				} else if (val1 instanceof Boolean && val2 instanceof Boolean) {
					comparison = ((Boolean) val1).compareTo((Boolean) val2);
				} else if (val1 instanceof Number && val2 instanceof Number) {
					comparison = Double.compare(((Number) val1).doubleValue(),
							((Number) val2).doubleValue());
				} else {
					logger
							.warn("Cannot compare row contents of class "
									+ val1.getClass() + " and "
									+ val2.getClass() + ".");
				}
			}

			if (comparison != 0) {
				return direction == SortOrder.DESCENDING ? -comparison
						: comparison;
			}
			return 0;
		}
	}
}
