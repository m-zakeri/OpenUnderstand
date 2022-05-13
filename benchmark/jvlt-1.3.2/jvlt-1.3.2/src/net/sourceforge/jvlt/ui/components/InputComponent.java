package net.sourceforge.jvlt.ui.components;

import javax.swing.JComponent;

public interface InputComponent {
	JComponent getComponent();

	Object getInput();

	void setInput(Object input);

	void reset();
}
