package net.sourceforge.jvlt.ui.components;

import java.awt.Component;
import java.awt.GridBagLayout;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Iterator;
import java.util.List;

import javax.swing.Box;
import javax.swing.JButton;
import javax.swing.JPanel;
import javax.swing.SwingConstants;

import net.sourceforge.jvlt.ui.utils.CustomConstraints;

public class ButtonPanel extends JPanel {
	private static final long serialVersionUID = 1L;

	private final int _alignment;
	private final int _orientation;
	private final List<JButton> _buttons;

	/**
	 * @param orientation SwingConstants.HORIZONTAL or SwingConstants.VERTICAL
	 * @param alignment SwingConstants.LEFT, SwingConstants.RIGHT,
	 *            SwingConstants.TOP or SwingConstants.BOTTOM)
	 */
	public ButtonPanel(int orientation, int alignment) {
		_buttons = new ArrayList<JButton>();
		_alignment = alignment;
		_orientation = orientation;

		setLayout(new GridBagLayout());
	}

	public ButtonPanel() {
		this(SwingConstants.HORIZONTAL, SwingConstants.RIGHT);
	}

	public void addButton(JButton button) {
		_buttons.add(button);
		resetLayout();
	}

	public void addButtons(JButton[] buttons) {
		_buttons.addAll(Arrays.asList(buttons));
		resetLayout();
	}

	public void setButtons(JButton[] buttons) {
		_buttons.clear();
		addButtons(buttons);
	}

	private void resetLayout() {
		Component[] components = getComponents();
		for (Component component2 : components) {
			remove(component2);
		}

		CustomConstraints cc = new CustomConstraints();
		int i = 0;
		if (_alignment == SwingConstants.RIGHT
				|| _alignment == SwingConstants.BOTTOM) {
			if (_orientation == SwingConstants.HORIZONTAL) {
				cc.update(i++, 0, 1.0, 0.0);
			} else {
				cc.update(0, i++, 0.0, 1.0);
			}
			add(Box.createHorizontalGlue(), cc);
		}

		Iterator<JButton> it = _buttons.iterator();
		while (it.hasNext()) {
			JButton button = it.next();
			if (_orientation == SwingConstants.HORIZONTAL) {
				cc.update(i++, 0, 0.0, 0.0);
			} else {
				cc.update(0, i++, 0.0, 0.0);
			}
			add(button, cc);
		}

		if (_alignment == SwingConstants.LEFT
				|| _alignment == SwingConstants.TOP) {
			if (_orientation == SwingConstants.HORIZONTAL) {
				cc.update(i, 0, 1.0, 0.0);
			} else {
				cc.update(0, i, 0.0, 1.0);
			}
			add(Box.createHorizontalGlue(), cc);
		}
	}
}
