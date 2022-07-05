package net.sourceforge.jvlt.ui.wizard;

import javax.swing.JComponent;

public abstract class WizardPanelDescriptor {
	protected WizardModel _model;
	protected JComponent _panel;

	public WizardPanelDescriptor() {
		this(null);
	}

	public WizardPanelDescriptor(WizardModel model) {
		_model = model;
		_panel = null;
	}

	public abstract String getID();

	public JComponent getPanelComponent() {
		return _panel;
	}

	/**
	 * This method is called before the panel descriptor is shown. It can - for
	 * example - be used to set focus to a specific component.
	 */
	public void prepareToShow() {
		// empty default implementation
	}
}
