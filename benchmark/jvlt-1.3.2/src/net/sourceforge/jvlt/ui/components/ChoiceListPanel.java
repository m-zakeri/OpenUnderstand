package net.sourceforge.jvlt.ui.components;

import net.sourceforge.jvlt.utils.ItemContainer;

/**
 * A panel for managing lists of objects. The items that are added to the list
 * are selected via a combo box. The objects available in the combo box can be
 * set by calling {@link #setAvailableObjects}. Method
 * {@link #setAllowCustomChoices} allows to make the combo box editable, so that
 * arbitrary strings can be added.
 */
public class ChoiceListPanel extends ObjectListPanel {
	private static final long serialVersionUID = 1L;

	protected ItemContainer _container;

	public ChoiceListPanel() {
		this(new ChoiceInputComponent());
	}

	@Override
	public Object[] getSelectedObjects() {
		return _container.getItems(super.getSelectedObjects());
	}

	public void setAvailableObjects(Object[] objects) {
		((ChoiceInputComponent) _input_component).setChoices(objects);
		_container.setItems(objects);
		update();
	}

	public void setTranslateItems(boolean translate) {
		_container.setTranslateItems(translate);
		((ChoiceInputComponent) _input_component).setTranslateItems(translate);
	}

	public void setAllowCustomChoices(boolean allow) {
		((ChoiceInputComponent) _input_component).setAllowCustomChoices(allow);
	}

	protected ChoiceListPanel(ListeningInputComponent c) {
		super(c);
		_container = new ItemContainer();
	}

	@Override
	protected String toString(Object o) {
		return _container == null ? null : _container.getTranslation(o);
	}
}
