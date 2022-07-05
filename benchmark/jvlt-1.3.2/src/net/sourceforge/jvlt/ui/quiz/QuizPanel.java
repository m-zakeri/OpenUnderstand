package net.sourceforge.jvlt.ui.quiz;

import java.awt.BorderLayout;

import javax.swing.JPanel;

import net.sourceforge.jvlt.event.SelectionNotifier;
import net.sourceforge.jvlt.model.JVLTModel;
import net.sourceforge.jvlt.ui.wizard.Wizard;

public class QuizPanel extends JPanel {
	private static final long serialVersionUID = 1L;

	private final JVLTModel _model;
	private final Wizard _wizard;

	public QuizPanel(JVLTModel model, SelectionNotifier notifier) {
		_model = model;
		_wizard = new Wizard(new QuizModel(_model, notifier));

		setLayout(new BorderLayout());
		add(_wizard.getContent());
	}

	public Wizard getWizard() {
		return _wizard;
	}
}
