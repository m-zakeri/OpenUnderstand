package net.sourceforge.jvlt.ui.quiz;

import java.awt.GridBagLayout;
import java.awt.event.ItemEvent;
import java.awt.event.ItemListener;
import java.util.ArrayList;
import java.util.Iterator;

import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JRadioButton;

import net.sourceforge.jvlt.event.StateListener;
import net.sourceforge.jvlt.event.StateListener.StateEvent;
import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.ui.utils.GUIUtils;

public class YesNoPanel extends JPanel implements ItemListener {
	public static final int YES_OPTION = 0;
	public static final int NO_OPTION = 1;
	public static final int UNKNOWN_OPTION = 2;

	private static final long serialVersionUID = 1L;

	private JLabel _message_label;
	private JRadioButton _yes_button;
	private JRadioButton _no_button;

	private final ArrayList<StateListener> _listeners;

	public YesNoPanel(String message) {
		_listeners = new ArrayList<StateListener>();
		init();
		setMessage(message);
	}

	public void itemStateChanged(ItemEvent ev) {
		int state = UNKNOWN_OPTION;
		if (ev.getItem() == _yes_button) {
			if (ev.getStateChange() == ItemEvent.SELECTED) {
				_no_button.setSelected(false);
				state = YES_OPTION;
			}
		} else if (ev.getItem() == _no_button) {
			if (ev.getStateChange() == ItemEvent.SELECTED) {
				_yes_button.setSelected(false);
				state = NO_OPTION;
			}
		}

		Iterator<StateListener> it = _listeners.iterator();
		while (it.hasNext()) {
			StateListener listener = it.next();
			listener.stateChanged(new StateEvent(this, state));
		}
	}

	public int getState() {
		if (_yes_button.isSelected()) {
			return YES_OPTION;
		} else if (_no_button.isSelected()) {
			return NO_OPTION;
		} else {
			return UNKNOWN_OPTION;
		}
	}

	public void setState(int state) {
		_yes_button.setSelected(false);
		_no_button.setSelected(false);

		if (state == YES_OPTION) {
			_yes_button.setSelected(true);
		} else if (state == NO_OPTION) {
			_no_button.setSelected(true);
		}
	}

	public void setMessage(String msg) {
		_message_label.setText(msg);
	}

	public void addStateListener(StateListener l) {
		_listeners.add(l);
	}

	public void removeStateListener(StateListener l) {
		_listeners.remove(l);
	}

	private void init() {
		_yes_button = new JRadioButton(GUIUtils.createTextAction("yes"));
		_no_button = new JRadioButton(GUIUtils.createTextAction("no"));
		_yes_button.addItemListener(this);
		_no_button.addItemListener(this);
		_message_label = new JLabel();

		setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1.0, 1.0);
		add(_message_label, cc);
		cc.update(1, 0, 0.0, 0.0);
		add(_yes_button, cc);
		cc.update(2, 0, 0.0, 0.0);
		add(_no_button, cc);
	}
}
