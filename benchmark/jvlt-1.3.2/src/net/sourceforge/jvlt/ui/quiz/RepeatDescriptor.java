package net.sourceforge.jvlt.ui.quiz;

import javax.swing.JPanel;

import net.sourceforge.jvlt.ui.wizard.WizardModel;
import net.sourceforge.jvlt.utils.I18nService;

class RepeatDescriptor extends YesNoDescriptor {
	public RepeatDescriptor(WizardModel model) {
		super(model, I18nService.getString("Messages", "repeat_words"));
		setContentPanel(new JPanel());
	}

	@Override
	public String getID() {
		return "repeat";
	}
}
