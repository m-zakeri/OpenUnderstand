package net.sourceforge.jvlt.ui.utils;

import java.awt.GridBagConstraints;
import java.awt.Insets;

public class CustomConstraints extends GridBagConstraints {
	private static final long serialVersionUID = 1L;

	public CustomConstraints() {
		fill = GridBagConstraints.BOTH;
		insets = new Insets(2, 2, 2, 2);
	}

	public void update(int x, int y) {
		gridx = x;
		gridy = y;
	}

	public void update(int x, int y, double weight_x, double weight_y) {
		update(x, y);

		weightx = weight_x;
		weighty = weight_y;
	}

	public void update(int x, int y, double weight_x, double weight_y,
			int grid_width, int grid_height) {
		update(x, y, weight_x, weight_y);

		gridwidth = grid_width;
		gridheight = grid_height;
	}

	public void reset() {
		fill = GridBagConstraints.BOTH;
		update(0, 0, 0.0, 0.0, 1, 1);
	}
}
