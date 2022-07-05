package net.sourceforge.jvlt.ui.components;

import java.util.ArrayList;
import java.util.TreeSet;

import net.sourceforge.jvlt.core.AttributeChoice;

public class AttributeChoiceInputComponent extends ChoiceInputComponent {
	public AttributeChoiceInputComponent() {
		super(new IndentedComboBox());
		setTranslateItems(true);
	}

	@Override
	protected void updateInputComponent() {
		Object[] choices = _container.getItems();
		TreeSet<AttributeChoice> root_set = new TreeSet<AttributeChoice>();
		ArrayList<AttributeChoice> roots = new ArrayList<AttributeChoice>();
		for (Object choice2 : choices) {
			AttributeChoice choice = (AttributeChoice) choice2;
			if (choice.getParent() == null && !root_set.contains(choice)) {
				roots.add(choice);
				root_set.add(choice);
			}
		}

		for (AttributeChoice attributeChoice : roots) {
			insertChoice(attributeChoice, 0);
		}

		if (choices.length > 0) {
			_input_box.setSelectedIndex(0);
		}
	}

	private void insertChoice(AttributeChoice choice, int indent_level) {
		((IndentedComboBox) _input_box).addItem(_container
				.getTranslation(choice), indent_level);
		AttributeChoice[] children = choice.getChildren();
		for (AttributeChoice element : children) {
			insertChoice(element, indent_level + 1);
		}
	}
}
