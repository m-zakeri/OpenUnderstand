package net.sourceforge.jvlt.ui.dialogs;

import java.awt.Component;
import java.awt.Dimension;
import java.awt.Font;
import java.awt.Frame;
import java.awt.GraphicsEnvironment;
import java.awt.GridBagLayout;
import java.awt.GridLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.util.ArrayList;
import java.util.Iterator;

import javax.swing.Action;
import javax.swing.Box;
import javax.swing.JButton;
import javax.swing.JCheckBox;
import javax.swing.JDialog;
import javax.swing.JList;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.border.EtchedBorder;
import javax.swing.border.TitledBorder;
import javax.swing.event.ListSelectionEvent;
import javax.swing.event.ListSelectionListener;

import net.sourceforge.jvlt.ui.components.CustomTextField;
import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.ui.utils.FontInfo;
import net.sourceforge.jvlt.ui.utils.GUIUtils;
import net.sourceforge.jvlt.utils.I18nService;

public class FontChooser implements ActionListener, ListSelectionListener {
	private int _option;
	private final InputList _font_list;
	private final InputList _size_list;
	private final JCheckBox _bold_box;
	private final JCheckBox _italic_box;
	private JDialog _dlg;
	private final JPanel _content_pane;
	private final CustomTextField _preview_field;

	public FontChooser() {
		GraphicsEnvironment ge = GraphicsEnvironment
				.getLocalGraphicsEnvironment();
		_font_list = new InputList(ge.getAvailableFontFamilyNames(),
				"font_family");
		_font_list.addListSelectionListener(this);
		String[] font_sizes = new String[] { "8", "9", "10", "11", "12", "14",
				"16", "18", "20", "22", "24", "26", "28", "36", "48", "72" };
		_size_list = new InputList(font_sizes, "font_size");
		_size_list.addListSelectionListener(this);
		_bold_box = new JCheckBox(I18nService.getString("Labels", "font_bold"));
		_bold_box.setActionCommand("bold");
		_bold_box.addActionListener(this);
		_italic_box = new JCheckBox(I18nService.getString("Labels", "font_italic"));
		_italic_box.setActionCommand("italic");
		_italic_box.addActionListener(this);

		JPanel preview_panel = new JPanel();
		preview_panel
				.setBorder(new TitledBorder(new EtchedBorder(
						EtchedBorder.LOWERED), I18nService.getString("Labels",
						"preview")));
		_preview_field = new CustomTextField(20);
		_preview_field.setText("abcdefghijklmNOPQRSTUVWXYZ");
		JScrollPane preview_spane = new JScrollPane(_preview_field);
		preview_spane.setPreferredSize(new Dimension(100, 50));
		preview_panel.setLayout(new GridLayout());
		preview_panel.add(preview_spane);

		Action ok_action = GUIUtils.createTextAction(this, "ok");
		Action cancel_action = GUIUtils.createTextAction(this, "cancel");

		JPanel selection_panel = new JPanel();
		selection_panel.setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1.0, 1.0);
		selection_panel.add(_font_list, cc);
		cc.update(1, 0, 1.0, 1.0);
		selection_panel.add(_size_list, cc);

		JPanel style_panel = new JPanel();
		style_panel.setLayout(new GridBagLayout());
		style_panel.setBorder(new TitledBorder(new EtchedBorder(
				EtchedBorder.LOWERED), I18nService.getString("Labels",
				"font_style")));
		cc.update(0, 0, 1.0, 0.0);
		style_panel.add(_bold_box, cc);
		cc.update(1, 0, 1.0, 0.0);
		style_panel.add(_italic_box, cc);

		JPanel button_panel = new JPanel();
		button_panel.setLayout(new GridBagLayout());
		cc.update(0, 0, 1.0, 0.0);
		button_panel.add(Box.createHorizontalGlue(), cc);
		cc.update(1, 0, 0.0, 0.0);
		button_panel.add(new JButton(ok_action), cc);
		cc.update(2, 0, 0.0, 0.0);
		button_panel.add(new JButton(cancel_action), cc);

		_content_pane = new JPanel();
		_content_pane.setLayout(new GridBagLayout());
		cc.update(0, 0, 1.0, 0.75);
		_content_pane.add(selection_panel, cc);
		cc.update(0, 1, 1.0, 0.0);
		_content_pane.add(style_panel, cc);
		cc.update(0, 2, 1.0, 0.25);
		_content_pane.add(preview_panel, cc);
		cc.update(0, 3, 1.0, 0.0);
		_content_pane.add(button_panel, cc);
	}

	public FontInfo getFontInfo() {
		int style;
		if (!_bold_box.isSelected() && !_italic_box.isSelected()) {
			style = Font.PLAIN;
		} else {
			style = 0;
			if (_bold_box.isSelected()) {
				style += Font.BOLD;
			}
			if (_italic_box.isSelected()) {
				style += Font.ITALIC;
			}
		}

		int size;
		try {
			size = Integer.parseInt(_size_list.getSelectedString());
		} catch (NumberFormatException ex) {
			size = 12;
		}

		return new FontInfo(_font_list.getSelectedString(), style, size);
	}

	public void setFontInfo(FontInfo info) {
		if (info == null) {
			_font_list.setSelectedString(null);
			_size_list.setSelectedString(null);
			_bold_box.setSelected(false);
			_italic_box.setSelected(false);
		} else {
			_font_list.setSelectedString(info.getFamily());
			_size_list.setSelectedString(String.valueOf(info.getSize()));
			_bold_box.setSelected((info.getStyle() & Font.BOLD) != 0);
			_italic_box.setSelected((info.getStyle() & Font.ITALIC) != 0);
		}

		updatePreview();
	}

	public void actionPerformed(ActionEvent ev) {
		if (ev.getActionCommand().equals("ok")) {
			_option = JOptionPane.OK_OPTION;
			_dlg.setVisible(false);
		} else if (ev.getActionCommand().equals("cancel")) {
			_option = JOptionPane.CANCEL_OPTION;
			_dlg.setVisible(false);
		} else if (ev.getActionCommand().equals("bold")
				|| ev.getActionCommand().equals("italic")) {
			updatePreview();
		}
	}

	public void valueChanged(ListSelectionEvent ev) {
		if (!ev.getValueIsAdjusting()) {
			updatePreview();
		}
	}

	public int showDialog(Component parent) {
		Frame frame = JOptionPane.getFrameForComponent(parent);
		_dlg = new JDialog(frame, I18nService.getString("Labels", "select_font"),
				true);
		_dlg.setContentPane(_content_pane);
		_option = JOptionPane.CANCEL_OPTION;
		GUIUtils.showDialog(frame, _dlg);

		return _option;
	}

	private void updatePreview() {
		Font font = getFontInfo().getFont();
		_preview_field.setFont(font);
		_content_pane.revalidate();
	}
}

class InputList extends JPanel implements ListSelectionListener {
	private static final long serialVersionUID = 1L;

	private final ArrayList<ListSelectionListener> _listeners;
	private final CustomTextField _field;
	private final JList _list;

	public InputList(String[] data, String name) {
		_listeners = new ArrayList<ListSelectionListener>();

		_field = new CustomTextField(20);
		_field.setActionCommand(name);
		_list = new JList(data);
		_list.setVisibleRowCount(5);
		_list.addListSelectionListener(this);
		JScrollPane spane = new JScrollPane(_list);

		setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1.0, 0.0);
		add(_field.getLabel(), cc);
		cc.update(0, 1, 1.0, 0.0);
		add(_field, cc);
		cc.update(0, 2, 1.0, 1.0);
		add(spane, cc);
	}

	public String getSelectedString() {
		return _field.getText();
	}

	public void setSelectedString(String str) {
		_list.setSelectedValue(str, true);
		_field.setText(str);
	}

	public void valueChanged(ListSelectionEvent e) {
		if (!e.getValueIsAdjusting()) {
			Object obj = _list.getSelectedValue();
			if (obj != null) {
				_field.setText(obj.toString());
			}
		}

		Iterator<ListSelectionListener> it = _listeners.iterator();
		while (it.hasNext()) {
			it.next().valueChanged(e);
		}
	}

	public void addListSelectionListener(ListSelectionListener listener) {
		_listeners.add(listener);
	}
}
