package net.sourceforge.jvlt.ui.components;

import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;

import javax.swing.DefaultComboBoxModel;
import javax.swing.JComboBox;
import javax.swing.JLabel;
import javax.swing.JOptionPane;

import net.sourceforge.jvlt.ui.dialogs.FontChooser;
import net.sourceforge.jvlt.ui.utils.FontInfo;
import net.sourceforge.jvlt.ui.utils.GUIUtils;
import net.sourceforge.jvlt.utils.I18nService;

public class FontChooserComboBox extends JComboBox {
	public static final String DEFAULT_STRING = I18nService.getString("Labels",
			"use_default");
	public static final String CHOOSE_STRING = I18nService.getString("Labels",
			"choose_font");

	private class Model extends DefaultComboBoxModel {
		private static final long serialVersionUID = 1L;

		@Override
		public int getSize() {
			return fontInfo == null ? 2 : 3;
		}

		@Override
		public Object getElementAt(int index) {
			switch (index) {
			case 0:
				return DEFAULT_STRING;
			case 1:
				return fontInfo == null ? CHOOSE_STRING : fontInfo.getFamily()
						+ " " + fontInfo.getSize();
			case 2:
				return fontInfo == null ? null : CHOOSE_STRING;
			default:
				return null;
			}
		}

		public void update() {
			fireContentsChanged(this, 0, getSize());

			setSelectedItem(fontInfo == null ? I18nService.getString("Labels",
					"use_default") : fontInfo.getFamily() + " "
					+ fontInfo.getSize());
		}
	}

	private class ActionHandler implements ActionListener {
		public void actionPerformed(ActionEvent e) {
			Object selected = getSelectedItem();

			if (selected == DEFAULT_STRING) {
				fontInfo = null;
			} else if (getSelectedItem() == CHOOSE_STRING) {
				fontChooser.setFontInfo(fontInfo);
				int val = fontChooser.showDialog(FontChooserComboBox.this);
				if (val == JOptionPane.OK_OPTION) {
					setFontInfo(fontChooser.getFontInfo());
				}
			}
		}
	}

	private static final long serialVersionUID = 1L;

	private static FontChooser fontChooser = new FontChooser();

	private FontInfo fontInfo = null;
	private final Model model = new Model();
	private JLabel label = null;

	public FontChooserComboBox() {
		setModel(model);
		addActionListener(new ActionHandler());

		model.update();
	}

	public FontInfo getFontInfo() {
		return fontInfo;
	}

	public void setFontInfo(FontInfo fontInfo) {
		FontInfo oldInfo = this.fontInfo;
		this.fontInfo = fontInfo;

		if (oldInfo != fontInfo) {
			model.update();
		}
	}

	public JLabel getJLabel() {
		return label;
	}

	@Override
	public void setActionCommand(String command) {
		super.setActionCommand(command);
		label = GUIUtils.getLabel(command, this);
	}
}
