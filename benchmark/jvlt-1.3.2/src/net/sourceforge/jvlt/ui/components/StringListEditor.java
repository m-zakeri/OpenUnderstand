package net.sourceforge.jvlt.ui.components;

import javax.swing.JComponent;

public class StringListEditor extends ObjectListEditor {
	public StringListEditor(String label) {
		super(label);
	}

	@Override
	protected InputComponent createSingleInputComponent() {
		return new StringInputComponent();
	}

	@Override
	protected InputComponent createMultiInputComponent() {
		return new StringListInputComponent();
	}
}

class StringListInputComponent implements InputComponent {
	private final ObjectListPanel _input_component = new ObjectListPanel();

	public JComponent getComponent() {
		return _input_component;
	}

	public Object getInput() {
		return _input_component.getSelectedObjects();
	}

	public void setInput(Object input) {
		_input_component.setSelectedObjects((Object[]) input);
	}

	public void reset() {
		_input_component.setSelectedObjects(new Object[0]);
	}
}
