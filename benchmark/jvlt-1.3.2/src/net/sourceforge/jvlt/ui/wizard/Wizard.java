package net.sourceforge.jvlt.ui.wizard;

import java.awt.GridBagLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.awt.event.KeyEvent;

import javax.swing.Action;
import javax.swing.Box;
import javax.swing.JButton;
import javax.swing.JLabel;
import javax.swing.JPanel;

import net.sourceforge.jvlt.ui.dialogs.MessageDialog;
import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.ui.utils.GUIUtils;

public class Wizard implements ActionListener {
	public static final String CANCEL_COMMAND = "cancel";
	public static final String NEXT_COMMAND = "next";
	public static final String BACK_COMMAND = "back";

	protected WizardModel _model;

	protected JLabel _status_label;
	protected JPanel _content;
	protected Action _cancel_action;
	protected Action _next_action;
	protected Action _back_action;
	protected JButton _cancel_button;
	protected JButton _next_button;
	protected JButton _back_button;

	public Wizard(WizardModel model) {
		_model = model;
		_model.setWizard(this);
		init();
		showPanel(_model.getCurrentPanelDescriptor());
	}

	public WizardModel getModel() {
		return _model;
	}

	public JPanel getContent() {
		return _content;
	}

	public JButton getDefaultButton() {
		String button_command = _model.getDefaultButton();
		if (button_command.equals(CANCEL_COMMAND)) {
			return _cancel_button;
		} else if (button_command.equals(NEXT_COMMAND)) {
			return _next_button;
		} else if (button_command.equals(BACK_COMMAND)) {
			return _back_button;
		} else {
			return null;
		}
	}

	public void actionPerformed(ActionEvent ev) {
		String command = ev.getActionCommand();
		if (command.equals(CANCEL_COMMAND) || command.equals(NEXT_COMMAND)
				|| command.equals(BACK_COMMAND)) {
			try {
				WizardPanelDescriptor old_descriptor = _model
						.getCurrentPanelDescriptor();
				WizardPanelDescriptor new_descriptor = _model
						.nextPanelDescriptor(command);
				hidePanel(old_descriptor);
				showPanel(new_descriptor);
			} catch (WizardModel.InvalidInputException e) {
				MessageDialog.showDialog(_content,
						MessageDialog.WARNING_MESSAGE, e.getShortMessage(), e
								.getLongMessage());
			}
		}
	}

	public void panelDescriptorUpdated() {
		updateButtons();
	}

	public void newPanelDescriptorSelected(
			WizardPanelDescriptor old_descriptor,
			WizardPanelDescriptor new_descriptor) {
		hidePanel(old_descriptor);
		showPanel(new_descriptor);

		updateButtons();
	}

	private void init() {
		_cancel_action = GUIUtils.createTextAction(this, CANCEL_COMMAND);
		_next_action = GUIUtils.createTextAction(this, NEXT_COMMAND);
		_back_action = GUIUtils.createTextAction(this, BACK_COMMAND);
		_cancel_button = new JButton(_cancel_action);
		_back_button = new JButton(_back_action);
		_next_button = new JButton(_next_action);

		JPanel button_panel = new JPanel();
		button_panel.setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1.0, 0.0);
		button_panel.add(Box.createHorizontalGlue(), cc);
		cc.update(1, 0, 0.0, 0.0);
		button_panel.add(_back_button, cc);
		cc.update(2, 0, 0.0, 0.0);
		button_panel.add(_next_button, cc);
		cc.update(3, 0, 0.0, 0.0);
		button_panel.add(_cancel_button, cc);

		_status_label = new JLabel();
		_content = new JPanel();
		_content.setLayout(new GridBagLayout());
		cc.update(0, 0, 1.0, 0.0);
		_content.add(_status_label, cc);
		cc.update(0, 2, 1.0, 0.0);
		_content.add(button_panel, cc);
	}

	private void hidePanel(WizardPanelDescriptor panel) {
		_content.remove(panel.getPanelComponent());
	}

	private void showPanel(WizardPanelDescriptor panel) {
		updateButtons();
		_status_label.setText(_model.getStatusString());

		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 1, 1.0, 1.0);
		_content.add(panel.getPanelComponent(), cc);
		_content.revalidate();
		_content.repaint(_content.getVisibleRect());

		panel.prepareToShow();
	}

	private void setActionText(Action action, String text) {
		Integer mnemonic = GUIUtils.getMnemonicKey(text);
		action.putValue(Action.MNEMONIC_KEY, (int) KeyEvent.CHAR_UNDEFINED);
		String textToUse = text;
		if (mnemonic != null) {
			action.putValue(Action.MNEMONIC_KEY, mnemonic);
			textToUse = text.replaceAll("\\$", "");
		}

		action.putValue(Action.NAME, textToUse);
	}

	private void updateButtons() {
		_cancel_action.setEnabled(_model.isButtonEnabled(CANCEL_COMMAND));
		_next_action.setEnabled(_model.isButtonEnabled(NEXT_COMMAND));
		_back_action.setEnabled(_model.isButtonEnabled(BACK_COMMAND));
		setActionText(_cancel_action, _model.getButtonText(CANCEL_COMMAND));
		setActionText(_next_action, _model.getButtonText(NEXT_COMMAND));
		setActionText(_back_action, _model.getButtonText(BACK_COMMAND));
	}
}
