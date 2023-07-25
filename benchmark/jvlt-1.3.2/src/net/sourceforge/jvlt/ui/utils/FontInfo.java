package net.sourceforge.jvlt.ui.utils;

import java.awt.Font;

public class FontInfo {
	private String _family = null;
	private int _size = 0;
	private int _style = 0;

	public FontInfo(String family, int style, int size) {
		_family = family;
		_style = style;
		_size = size;
	}

	public FontInfo(Font font) {
		if (font != null) {
			_family = font.getFamily();
			_style = font.getStyle();
			_size = font.getSize();
		}
	}

	public String getFamily() {
		return _family;
	}

	public int getSize() {
		return _size;
	}

	public int getStyle() {
		return _style;
	}

	public Font getFont() {
		return new Font(_family, _style, _size);
	}
}
