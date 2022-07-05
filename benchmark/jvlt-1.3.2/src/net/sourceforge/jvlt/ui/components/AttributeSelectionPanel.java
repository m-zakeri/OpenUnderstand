package net.sourceforge.jvlt.ui.components;

import net.sourceforge.jvlt.metadata.AttributeComparator;

public class AttributeSelectionPanel extends ObjectSelectionPanel {
	private static final long serialVersionUID = 1L;

	public AttributeSelectionPanel() {
		super();
		setTranslateItems(true);
		setComparator(new AttributeComparator(_container));
	}
}
