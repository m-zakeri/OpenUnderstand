package net.sourceforge.jvlt.ui.dialogs;

import java.awt.Component;
import java.awt.Dialog;
import java.awt.Dimension;
import java.awt.Frame;
import java.awt.GridBagLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.net.URL;

import javax.swing.Action;
import javax.swing.Box;
import javax.swing.ImageIcon;
import javax.swing.JButton;
import javax.swing.JDialog;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JTextArea;
import javax.swing.border.EmptyBorder;
import javax.swing.border.EtchedBorder;
import javax.swing.border.TitledBorder;

import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.ui.utils.GUIUtils;
import net.sourceforge.jvlt.utils.I18nService;

public class MessageDialog extends JDialog implements ActionListener {
	private static final long serialVersionUID = 1L;

	public static final int WARNING_MESSAGE = 0;
	public static final int ERROR_MESSAGE = 1;
	public static final int INFO_MESSAGE = 2;
	public static final int OK_OPTION = 4;
	public static final int CANCEL_OPTION = 8;
	public static final int OK_CANCEL_OPTION = OK_OPTION | CANCEL_OPTION;
	public static final int USER_OPTION = 16;

	protected static MessageDialog _dialog = null;

	protected boolean _show_details = false;
	protected int _options = OK_OPTION;
	protected int _result = OK_OPTION;

	protected Action _details_action;
	protected JButton _ok_button;
	protected JButton _cancel_button;
	protected JButton _details_button;
	protected JLabel _message_label;
	protected JScrollPane _details_scrpane;
	protected JTextArea _details_area;
	protected JLabel _icon_label;
	protected JPanel _button_panel;
	protected JPanel _content_pane;
	protected String _details;

	public MessageDialog(Frame parent, int type, int options, String message,
			String details) {
		super(parent, true);
		_options = options;
		init(type, message, details);
	}

	public MessageDialog(Dialog parent, int type, int options, String message,
			String details) {
		super(parent, true);
		_options = options;
		init(type, message, details);
	}

	public MessageDialog(Frame parent, int type, String message, String details) {
		this(parent, type, OK_OPTION, message, details);
	}

	public MessageDialog(Dialog parent, int type, String message, String details) {
		this(parent, type, OK_OPTION, message, details);
	}

	public int getResult() {
		return _result;
	}

	public static int showDialog(Component parent, int type, int options,
			String message) {
		return showDialog(parent, type, options, message, null);
	}

	public static int showDialog(Component parent, int type, String message) {
		return showDialog(parent, type, message, null);
	}

	public static int showDialog(Component parent, int type, String message,
			String details) {
		return showDialog(parent, type, OK_OPTION, message, details);
	}

	public static int showDialog(Component parent, int type, int options,
			String message, String details) {
		Component comp = GUIUtils.getFrameOrDialogForComponent(parent);
		if (comp instanceof Dialog) {
			_dialog = new MessageDialog((Dialog) comp, type, options, message,
					details);
		} else {
			// if (comp instanceof Frame)
			_dialog = new MessageDialog((Frame) comp, type, options, message,
					details);
		}

		GUIUtils.showDialog(comp, _dialog);
		return _dialog._result;
	}

	public void actionPerformed(ActionEvent ev) {
		if (ev.getActionCommand().equals("ok")) {
			_result = OK_OPTION;
			setVisible(false);
		} else if (ev.getActionCommand().equals("cancel")) {
			_result = CANCEL_OPTION;
			setVisible(false);
		} else if (ev.getActionCommand().equals("details")) {
			_show_details = !_show_details;
			update();
		}
	}

	protected void initUI() {
		Action ok_action = GUIUtils.createTextAction(this, "ok");
		Action cancel_action = GUIUtils.createTextAction(this, "cancel");
		_details_action = GUIUtils.createAnonymousAction(this, "details");
		_message_label = new JLabel();
		_message_label.setBorder(new EmptyBorder(5, 5, 5, 5));
		_details_area = new JTextArea();
		_details_area.setEditable(false);
		_details_area.setOpaque(false);
		_details_scrpane = new JScrollPane(_details_area);
		_details_scrpane.setPreferredSize(new Dimension(300, 100));
		_details_scrpane
				.setBorder(new TitledBorder(new EtchedBorder(
						EtchedBorder.LOWERED), I18nService.getString("Labels",
						"details")));
		_icon_label = new JLabel();
		_details_button = new JButton(_details_action);
		_ok_button = new JButton(ok_action);
		_cancel_button = new JButton(cancel_action);
		_button_panel = new JPanel();
		_button_panel.setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1.0, 0.0);
		_button_panel.add(Box.createHorizontalGlue(), cc);

		_content_pane = new JPanel();
		_content_pane.setLayout(new GridBagLayout());
		cc.update(0, 0, 0.0, 1.0);
		_content_pane.add(_icon_label, cc);
		cc.update(1, 0, 1.0, 1.0);
		_content_pane.add(_message_label, cc);
		_content_pane.add(_details_scrpane);
		setContentPane(_content_pane);
	}

	protected void updateButtonRow() {
		CustomConstraints cc = new CustomConstraints();
		_button_panel.remove(_ok_button);
		_button_panel.remove(_cancel_button);
		_button_panel.remove(_details_button);
		int x = 1;
		if ((_options & OK_OPTION) != 0) {
			cc.update(x++, 0, 0.0, 0.0);
			_button_panel.add(_ok_button, cc);
		}
		if ((_options & CANCEL_OPTION) != 0) {
			cc.update(x++, 0, 0.0, 0.0);
			_button_panel.add(_cancel_button, cc);
		}
		if (_details != null && !_details.equals("")) {
			cc.update(x++, 0, 0.0, 0.0);
			_button_panel.add(_details_button, cc);
		}
	}

	private void setMessages(String message, String details) {
		_details = details;
		_message_label.setText(message);
		_details_area.setText(details);
	}

	private void setIcon(String name) {
		String image_path = "/images/" + name + ".png";
		URL image_url = MessageDialog.class.getResource(image_path);
		_icon_label.setIcon(new ImageIcon(image_url));
	}

	private void init(int type, String message, String details) {
		String title = "";
		String icon = "";
		if (type == WARNING_MESSAGE) {
			title = I18nService.getString("Labels", "warning");
			icon = "msg_warning";
		} else if (type == ERROR_MESSAGE) {
			title = I18nService.getString("Labels", "error");
			icon = "msg_critical";
		} else if (type == INFO_MESSAGE) {
			title = I18nService.getString("Labels", "status");
			icon = "msg_info";
		}
		setTitle(title);

		initUI();
		setIcon(icon);
		setMessages(message, details);
		update();
	}

	private void update() {
		String text;
		if (_show_details) {
			text = I18nService.getString("Actions", "details_less");
		} else {
			text = I18nService.getString("Actions", "details_more");
		}
		Integer mnemonic = GUIUtils.getMnemonicKey(text);
		if (mnemonic != null) {
			_details_action.putValue(Action.MNEMONIC_KEY, mnemonic);
			text = text.replaceAll("\\$", "");
		}
		_details_action.putValue(Action.NAME, text);

		updateButtonRow();

		CustomConstraints cc = new CustomConstraints();
		_content_pane.remove(_details_scrpane);
		_content_pane.remove(_button_panel);
		int y = 1;
		if (_details != null && !_details.equals("") && _show_details) {
			cc.update(1, y++, 1.0, 1.0);
			_content_pane.add(_details_scrpane, cc);
		}

		cc.update(1, y, 1.0, 0.0);
		_content_pane.add(_button_panel, cc);

		_content_pane.revalidate();
		_content_pane.repaint(_content_pane.getVisibleRect());
		pack();
	}
}
