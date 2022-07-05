package net.sourceforge.jvlt.ui.dialogs;

import java.awt.Component;
import java.awt.Container;
import java.awt.Frame;
import java.awt.GridBagLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.awt.event.WindowAdapter;
import java.awt.event.WindowEvent;
import java.lang.reflect.Field;
import java.util.Iterator;
import java.util.LinkedList;
import java.util.List;

import javax.swing.Action;
import javax.swing.Box;
import javax.swing.JButton;
import javax.swing.JDialog;
import javax.swing.JPanel;
import javax.swing.border.EmptyBorder;

import org.apache.log4j.Logger;

import net.sourceforge.jvlt.event.DialogListener;
import net.sourceforge.jvlt.event.DialogListener.DialogEvent;
import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.ui.utils.GUIUtils;

public abstract class AbstractDialog extends JDialog implements ActionListener {
	private static final Logger logger = Logger.getLogger(AbstractDialog.class);
	public static final int OK_OPTION = 1;
	public static final int APPLY_OPTION = 2;
	public static final int CANCEL_OPTION = 3;
	public static final int CLOSE_OPTION = 4;
	public static final int USER_OPTION = 5;

	private static final long serialVersionUID = 1L;

	private int[] _buttons = new int[] { OK_OPTION, CANCEL_OPTION };
	private int _default_button = OK_OPTION;
	private final List<DialogListener> _listeners;

	private Container _content = null;
	private JPanel _button_panel = null;

	public AbstractDialog(Frame owner, String title, boolean modal) {
		super(owner, title, modal);

		_listeners = new LinkedList<DialogListener>();

		addWindowListener(new WindowAdapter() {
			@Override
			public void windowClosing(WindowEvent ev) {
				fireDialogEvent(new DialogEvent(AbstractDialog.this,
						CLOSE_OPTION));
			}
		});

		init();
	}

	public void addDialogListener(DialogListener l) {
		_listeners.add(l);
	}

	public void setContent(Container container) {
		_content = container;
		init();
	}

	public void setButtons(int[] buttons) {
		_buttons = buttons;
		init();
	}

	public void actionPerformed(ActionEvent ev) {
		String command = ev.getActionCommand();
		int value = getValueForFieldName(command);
		fireDialogEvent(new DialogEvent(this, value));
	}

	protected void fireDialogEvent(DialogEvent ev) {
		Iterator<DialogListener> it = _listeners.iterator();
		while (it.hasNext()) {
			it.next().dialogStateChanged(ev);
		}
	}

	public void setDefaultButton(int button) {
		_default_button = button;
		Component comp = getComponent(getFieldNameForValue(button));
		if (comp != null) {
			getRootPane().setDefaultButton((JButton) comp);
		}
	}

	protected String getFieldNameForValue(int value) {
		if (value >= USER_OPTION) {
			return getFieldNameForCustomValue(value);
		}

		Field[] fields = AbstractDialog.class.getFields();
		for (Field field : fields) {
			if (field.getType().getName().equals("int")) {
				try {
					int val = field.getInt(null);
					if (val == value) {
						return field.getName();
					}
				} catch (Exception ex) {
					logger.error(ex);
				}
			}
		}

		return null;
	}

	/**
	 * Function returning a field name for a custom value.
	 * 
	 * This function should be reimplemented by subclasses in order to support
	 * options that correspond to an integer value equal or greater than
	 * {@link AbstractDialog#USER_OPTION}.
	 */
	protected String getFieldNameForCustomValue(int value) {
		// value parameter must be available for subclasses
		return null;
	}

	protected int getValueForFieldName(String name) {
		try {
			Field[] fields = AbstractDialog.class.getFields();
			for (Field field : fields) {
				if (field.getName().equals(name)) {
					return field.getInt(null);
				}
			}

			return getValueForCustomFieldName(name);
		} catch (Exception ex) {
			logger.error(ex);
		}

		return -1;
	}

	/**
	 * Function for returning a value for a custom field name
	 * 
	 * This function should be reimplemented by subclasses in order to support
	 * custom options.
	 */
	protected int getValueForCustomFieldName(String name) {
		// name parameter must be available for subclasses
		return -1;
	}

	private Component getComponent(String name) {
		Component[] comps = _button_panel.getComponents();
		for (Component comp : comps) {
			String comp_name = comp.getName();
			if (comp_name == null) {
				continue;
			} else if (comp_name.equals(name)) {
				return comp;
			}
		}

		return null;
	}

	private void init() {
		JPanel content_pane = new JPanel();

		_button_panel = new JPanel();
		_button_panel.setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1.0, 0.0);
		_button_panel.add(Box.createHorizontalGlue(), cc);
		for (int i = 0; i < _buttons.length; i++) {
			String field_name = getFieldNameForValue(_buttons[i]);
			Action action = GUIUtils.createTextAction(this, field_name);
			JButton button = new JButton(action);
			button.setName(field_name);
			content_pane.getActionMap().put(field_name, action);
			cc.update(i + 1, 0, 0.0, 0.0);
			_button_panel.add(button, cc);
		}

		content_pane.setLayout(new GridBagLayout());
		cc.update(0, 0, 1.0, 1.0);
		if (_content == null) {
			content_pane.add(new JPanel(), cc);
		} else {
			content_pane.add(_content, cc);
		}
		cc.update(0, 1, 1.0, 0.0);
		content_pane.add(_button_panel, cc);
		content_pane.setBorder(new EmptyBorder(5, 5, 5, 5));

		setDefaultButton(_default_button);
		setContentPane(content_pane);
	}
}
