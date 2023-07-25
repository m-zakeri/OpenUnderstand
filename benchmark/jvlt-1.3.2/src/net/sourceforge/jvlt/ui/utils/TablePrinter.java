package net.sourceforge.jvlt.ui.utils;

import java.awt.Color;
import java.awt.Font;
import java.awt.FontMetrics;
import java.awt.Graphics;
import java.awt.Graphics2D;
import java.awt.font.LineMetrics;
import java.awt.geom.Rectangle2D;
import java.awt.print.PageFormat;
import java.awt.print.Printable;
import java.awt.print.PrinterException;
import java.awt.print.PrinterJob;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Vector;

import javax.swing.table.TableModel;

import net.sourceforge.jvlt.JVLT;
import net.sourceforge.jvlt.utils.I18nService;
import net.sourceforge.jvlt.utils.UIConfig;

public class TablePrinter implements Printable {
	private int _page_number = 0;
	private final double _vertical_spacing = 5.0;
	private Font _font = null;
	private HashMap<Integer, Double> _colwidth_map = null;
	// Contains the pages
	// Key: Name of a subclass of Graphics2D
	// Value: Vector of Integer, the ith element of the vector gives the index
	// of the last row of page i
	private HashMap<String, Vector<Integer>> _pages_map = null;
	private PageFormat _format = null;
	private TableModel _model = null;

	private static class ColumnInfo {
		int numCols;
		double colWidths[];
		double xOffsets[];
	}

	public TablePrinter() {
		PrinterJob job = PrinterJob.getPrinterJob();
		_format = job.defaultPage();
		_font = ((UIConfig) JVLT.getConfig()).getFontProperty("print_font");

		_colwidth_map = new HashMap<Integer, Double>();
		_pages_map = new HashMap<String, Vector<Integer>>();
	}

	public PageFormat getPageFormat() {
		return _format;
	}

	/**
	 * Returns the number of pages obtained by the last call of renderPages().
	 */
	public int getPageNumber() {
		return _page_number;
	}

	public void setDataModel(TableModel model) {
		_model = model;
		_pages_map.clear();
	}

	public void setColWidth(int col, int percent) {
		_colwidth_map.put(col, new Double(percent / 100.0));
		_pages_map.clear();
	}

	public void paintPage(Graphics2D g2d, int page) throws PrinterException {
		if (_font != null) {
			g2d.setFont(_font);
		}

		g2d.setColor(Color.white);
		g2d.fill(new Rectangle2D.Double(0, 0, _format.getWidth(), _format
				.getHeight()));
		g2d.setColor(Color.black);

		if (!_pages_map.containsKey(g2d.getClass().getName())) {
			renderPages(g2d);
		}
		Vector<Integer> pages = _pages_map.get(g2d.getClass().getName());
		if (page >= pages.size()) {
			return;
		}

		int first_row = getFirstRowOnPage(pages, page);
		int last_row = getLastRowOnPage(pages, page);
		ColumnInfo info = getColumnInfo(_format, _vertical_spacing, _model
				.getColumnCount());

		Rectangle2D r2d = new Rectangle2D.Double();
		r2d
				.setRect(0, _format.getImageableY(), 0, _format
						.getImageableHeight());
		for (int row = first_row; row <= last_row; row++) {
			double max_height = 0;
			for (int col = 0; col < info.numCols; col++) {
				r2d.setRect(info.xOffsets[col], r2d.getY(),
						info.colWidths[col], r2d.getHeight());
				double height = renderCell(g2d, r2d, _model
						.getValueAt(row, col).toString(), true);
				if (height > max_height) {
					max_height = height;
				}
			}
			r2d.setRect(r2d.getX(), r2d.getY() + max_height, r2d.getWidth(),
					r2d.getHeight() - max_height);
		}
	}

	public int print(Graphics graphics, PageFormat format, int page_index)
			throws PrinterException {
		setPageFormat(format);
		Graphics2D g2d = (Graphics2D) graphics;
		if (_font != null) {
			g2d.setFont(_font);
		}

		if (!_pages_map.containsKey(g2d.getClass().getName())) {
			renderPages(g2d);
		}
		Vector<Integer> pages = _pages_map.get(g2d.getClass().getName());
		if (page_index > pages.size()) {
			return Printable.NO_SUCH_PAGE;
		}

		paintPage(g2d, page_index);

		return Printable.PAGE_EXISTS;
	}

	public void setPageFormat(PageFormat format) {
		_format = format;
	}

	/**
	 * Render pages using the current page format.
	 * 
	 * @return Number of pages.
	 */
	public int renderPages(Graphics2D g2d) throws PrinterException {
		if (_model == null || _model.getRowCount() == 0) {
			return 0;
		}

		if (_font != null) {
			g2d.setFont(_font);
		}

		Vector<Integer> pages;
		if (_pages_map.containsKey(g2d.getClass().getName())) {
			pages = _pages_map.get(g2d.getClass().getName());
			pages.clear();
		} else {
			pages = new Vector<Integer>();
			_pages_map.put(g2d.getClass().getName(), pages);
		}

		int num_cols = _model.getColumnCount();
		ColumnInfo info = getColumnInfo(_format, _vertical_spacing, num_cols);

		Rectangle2D r2d = new Rectangle2D.Double();
		r2d.setRect(0, 0, 0, _format.getImageableHeight());
		int num_rows = _model.getRowCount();
		for (int row = 0; row < num_rows; row++) {
			double max_height = 0;
			boolean row_fits_on_page = true;
			for (int col = 0; col < num_cols; col++) {
				r2d.setRect(info.xOffsets[col], r2d.getY(),
						info.colWidths[col], r2d.getHeight());
				double height = renderCell(g2d, r2d, _model
						.getValueAt(row, col).toString(), false);
				if (height < 0) {
					// new page
					r2d.setRect(0, 0, 0, _format.getImageableHeight());
					pages.add(row - 1);
					row_fits_on_page = false;
					break;
				} else if (height > max_height) {
					max_height = height;
				}
			}
			if (row_fits_on_page) {
				r2d.setRect(r2d.getX(), r2d.getY() + max_height,
						r2d.getWidth(), r2d.getHeight() - max_height);
			} else {
				// Process row again on the next page.
				row--;
				if (getLastRowOnPage(pages, pages.size() - 1)
						- getFirstRowOnPage(pages, pages.size() - 1) < 0) {
					throw new PrinterException(I18nService.getString("Messages",
							"page_full"));
				}
			}
		}
		pages.add(num_rows - 1);
		_page_number = pages.size();

		return pages.size();
	}

	/**
	 * Renders a cell of the table.
	 * 
	 * @param rect The maximum size of the cell.
	 * @param str The string contained in the cell.
	 * @param paint Specifies whether the cell is painted or only its size is
	 *            calculated.
	 * @return If the string does not fit into <i>rect</i> then -1 is returned.
	 *         Otherwise, the minimum possible height of the cell is returned.
	 */
	private double renderCell(Graphics2D graphics, Rectangle2D rect,
			String str, boolean paint) {
		LineBreaker breaker = new LineBreaker(rect.getWidth(), rect.getHeight());
		LineBreaker.Result result = breaker.breakLines(graphics, str);
		if (result == null) {
			return -1.0;
		}

		if (paint) {
			double[] positions = result.getPositions();
			String[] rows = result.getRows();
			double y = rect.getY();
			for (int i = 0; i < rows.length; i++) {
				graphics.drawString(rows[i], (float) rect.getMinX(),
						(float) (y + positions[i]));
			}
		}

		return result.getHeight();
	}

	private ColumnInfo getColumnInfo(PageFormat format,
			double vertical_spacing, int num_cols) {
		ColumnInfo info = new ColumnInfo();
		info.numCols = num_cols;

		double col_percents[] = new double[num_cols];
		double remaining_ratio = 1.0;
		int num_novalue = 0;
		for (int col = 0; col < num_cols; col++) {
			Integer key = col;
			if (_colwidth_map.containsKey(key)) {
				double val = (_colwidth_map.get(key)).doubleValue();
				val = Math.min(remaining_ratio, val);
				col_percents[col] = val;
				remaining_ratio -= val;
			} else {
				col_percents[col] = -1;
				num_novalue++;
			}
		}
		info.colWidths = new double[num_cols];
		double total_width = format.getImageableWidth() - (num_cols - 1)
				* vertical_spacing;
		for (int col = 0; col < num_cols; col++) {
			if (col_percents[col] < 0) {
				info.colWidths[col] = remaining_ratio / num_novalue
						* total_width;
			} else {
				info.colWidths[col] = col_percents[col] * total_width;
			}
		}

		info.xOffsets = new double[num_cols];
		info.xOffsets[0] = format.getImageableX();
		for (int col = 1; col < num_cols; col++) {
			info.xOffsets[col] = info.xOffsets[col - 1]
					+ info.colWidths[col - 1] + vertical_spacing;
		}

		return info;
	}

	private int getFirstRowOnPage(Vector<Integer> pages, int page) {
		if (page == 0) {
			return 0;
		}
		return pages.elementAt(page - 1).intValue() + 1;
	}

	private int getLastRowOnPage(Vector<Integer> pages, int page) {
		return pages.elementAt(page).intValue();
	}
}

class LineBreaker {
	public static class Result {
		private double _height;
		private final ArrayList<String> _rows;
		private final ArrayList<Double> _positions;

		public Result() {
			_rows = new ArrayList<String>();
			_positions = new ArrayList<Double>();
		}

		public double getHeight() {
			return _height;
		}

		public double[] getPositions() {
			double[] positions = new double[_positions.size()];
			Iterator<Double> it = _positions.iterator();
			int i = 0;
			while (it.hasNext()) {
				positions[i++] = it.next().doubleValue();
			}

			return positions;
		}

		public String[] getRows() {
			return _rows.toArray(new String[0]);
		}

		public void setHeight(double height) {
			_height = height;
		}

		public void addRow(String row, double position) {
			_rows.add(row);
			_positions.add(new Double(position));
		}
	}

	private final double _width;
	private final double _max_height;

	public LineBreaker(double width, double max_height) {
		_width = width;
		_max_height = max_height;
	}

	public Result breakLines(Graphics2D graphics, String text) {
		FontMetrics metrics = graphics.getFontMetrics();
		String remaining = text;
		double height = 0;
		Result result = new Result();
		while (remaining.length() != 0) {
			Rectangle2D r2d = metrics.getStringBounds(remaining, graphics);

			height += r2d.getHeight();
			// There is not enough space to paint the string.
			if (height > _max_height) {
				return null;
			}

			if (r2d.getWidth() <= _width) {
				LineMetrics lm = metrics.getLineMetrics(remaining, graphics);
				result.addRow(remaining, height - lm.getDescent());
				break;
			}
			int last_pos = -1;
			while (true) {
				int pos = findBreak(remaining, last_pos + 1);
				if (pos < 0) {
					break;
				}

				Rectangle2D rec = metrics.getStringBounds(remaining, 0, pos,
						graphics);
				if (rec.getWidth() > _width) {
					break;
				}

				last_pos = pos;
			}
			if (last_pos >= 0) {
				String str = remaining.substring(0, last_pos);
				LineMetrics lm = metrics.getLineMetrics(str, graphics);
				result.addRow(str, height - lm.getDescent());
				int pos = findNonWhitespace(remaining, last_pos);
				if (pos < 0) {
					remaining = "";
				} else {
					remaining = remaining.substring(pos, remaining.length());
				}
			} else {
				int len = (int) (_width / r2d.getWidth() * remaining.length());
				Rectangle2D rec = metrics.getStringBounds(remaining, 0, len,
						graphics);
				if (rec.getWidth() < _width) {
					int new_len = len + 1;
					while (new_len < remaining.length()) {
						rec = metrics.getStringBounds(remaining, 0, new_len,
								graphics);
						if (rec.getWidth() >= _width) {
							len = new_len - 1;
							break;
						}

						new_len++;
					}
				} else {
					while (len > 0) {
						len--;
						rec = metrics.getStringBounds(remaining, 0, len,
								graphics);
						if (rec.getWidth() < _width) {
							break;
						}
					}
				}

				String str = remaining.substring(0, len);
				LineMetrics lm = metrics.getLineMetrics(str, graphics);
				result.addRow(str, height - lm.getDescent());
				remaining = remaining.substring(len, remaining.length());
			}
		}

		result.setHeight(height);
		return result;
	}

	private int findBreak(String str, int start) {
		for (int i = start; i < str.length(); i++) {
			if (Character.isWhitespace(str.charAt(i))) {
				return i;
			}
		}

		return -1;
	}

	private int findNonWhitespace(String str, int start) {
		for (int i = start; i < str.length(); i++) {
			if (!Character.isWhitespace(str.charAt(i))) {
				return i;
			}
		}

		return -1;
	}
}
