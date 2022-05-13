package net.sourceforge.jvlt.ui.wizard;

import java.util.ArrayList;

import net.sourceforge.jvlt.event.StateListener;
import net.sourceforge.jvlt.event.StateListener.StateEvent;
import net.sourceforge.jvlt.model.JVLTModel;

public abstract class DialogWizardModel extends WizardModel {
	public static final int CANCEL_STATE = 0;
	public static final int FINISH_STATE = 1;

	protected JVLTModel _model;
	protected ArrayList<StateListener> _listeners;

	public DialogWizardModel(JVLTModel model) {
		_model = model;
		_listeners = new ArrayList<StateListener>();
	}

	public JVLTModel getJVLTModel() {
		return _model;
	}

	public void addStateListener(StateListener l) {
		_listeners.add(l);
	}

	public void removeStateListener(StateListener l) {
		_listeners.remove(l);
	}

	protected void fireStateEvent(StateEvent ev) {
		for (StateListener stateListener : _listeners) {
			stateListener.stateChanged(ev);
		}
	}
}
