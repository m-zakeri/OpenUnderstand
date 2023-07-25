package net.sourceforge.jvlt.ui.quiz;

import java.awt.GridBagLayout;

import javax.swing.JComponent;
import javax.swing.JPanel;

import net.sourceforge.jvlt.event.StateListener;
import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.ui.wizard.WizardModel;
import net.sourceforge.jvlt.ui.wizard.WizardPanelDescriptor;
import net.sourceforge.jvlt.utils.I18nService;

abstract class YesNoDescriptor extends WizardPanelDescriptor implements
		StateListener {
	private YesNoPanel _yes_no_panel;
	private JComponent _content_panel;

	public YesNoDescriptor(WizardModel model, String message) {
		super(model);
		_content_panel = null;
		init();
		setMessage(message);
	}

	public void stateChanged(StateEvent ev) {
		_model.panelDescriptorUpdated();
	}

	public int getState() {
		return _yes_no_panel.getState();
	}

	public void setState(int state) {
		_yes_no_panel.setState(state);
	}

	public final void setMessage(String message) {
		_yes_no_panel.setMessage(message);
	}

	public void setContentPanel(JComponent content) {
		if (_content_panel != null) {
			_panel.remove(_content_panel);
		}

		_content_panel = content;

		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1.0, 1.0);
		_panel.add(content, cc);
	}

	private void init() {
		String msg = I18nService.getString("Messages", "repeat_words");
		_yes_no_panel = new YesNoPanel(msg);
		_yes_no_panel.addStateListener(this);

		_panel = new JPanel();
		_panel.setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 1, 1.0, 0.0);
		_panel.add(_yes_no_panel, cc);
	}
}

