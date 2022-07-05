package net.sourceforge.jvlt.ui.quiz;

import java.awt.GridBagLayout;

import javax.swing.JPanel;

import net.sourceforge.jvlt.event.SelectionNotifier;
import net.sourceforge.jvlt.event.StateListener;
import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.utils.I18nService;

class EntryAnswerDescriptor extends EntryDescriptor implements StateListener {
	private YesNoPanel _yes_no_panel;

	public EntryAnswerDescriptor(QuizModel m, SelectionNotifier n) {
		super(m, n);
	}

	@Override
	public String getID() {
		return "entry_answer";
	}

	public int getState() {
		return _yes_no_panel.getState();
	}

	public void setState(int state) {
		_yes_no_panel.setState(state);
	}

	public void stateChanged(StateEvent ev) {
		_model.panelDescriptorUpdated();
	}

	@Override
	protected void init() {
		String msg = I18nService.getString("Messages", "entry_known");
		_yes_no_panel = new YesNoPanel(msg);
		_yes_no_panel.addStateListener(this);

		_panel = new JPanel();
		_panel.setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1.0, 1.0);
		_panel.add(_info_panel, cc);
		cc.update(0, 1, 1.0, 0.0);
		_panel.add(_flag_panel, cc);
		cc.update(0, 2, 1.0, 0.0);
		_panel.add(_yes_no_panel, cc);
	}
}
