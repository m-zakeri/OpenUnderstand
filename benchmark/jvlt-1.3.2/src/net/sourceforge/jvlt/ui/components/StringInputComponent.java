package net.sourceforge.jvlt.ui.components;

import javax.swing.JComponent;
import javax.swing.event.ChangeEvent;
import javax.swing.event.ChangeListener;

public class StringInputComponent extends ListeningInputComponent {
	private final CustomTextField _input_panel = new CustomTextField(10);

	public StringInputComponent() {
		_input_panel.addChangeListener(new ChangeListener() {
			public void stateChanged(ChangeEvent e) {
				fireChangeEvent();
			}
		});
	}

	public JComponent getComponent() {
		return _input_panel;
	}

	public void reset() {
		_input_panel.setText("");
	}

	public Object getInput() {
		String text = _input_panel.getText();
		return text == null ? null : (text.equals("") ? null : text);
	}

	public void setInput(Object input) {
		if (input == null) {
			_input_panel.setText("");
		} else {
			_input_panel.setText(input.toString());
		}
	}
}
