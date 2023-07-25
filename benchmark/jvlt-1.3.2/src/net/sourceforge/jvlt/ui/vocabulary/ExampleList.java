package net.sourceforge.jvlt.ui.vocabulary;

import java.util.ArrayList;
import java.util.Collection;

import javax.swing.DefaultListModel;
import javax.swing.JList;

import net.sourceforge.jvlt.core.Example;

public class ExampleList extends JList {
	private static final long serialVersionUID = 1L;

	private Collection<Example> _examples;

	public ExampleList() {
		super(new DefaultListModel());
		_examples = new ArrayList<Example>();
	}

	public Collection<Example> getExamples() {
		return _examples;
	}

	public void setExamples(Collection<Example> examples) {
		_examples = examples;
		DefaultListModel model = (DefaultListModel) getModel();
		model.clear();
		for (Example example : examples) {
			model.addElement(example.toString());
		}
	}
}
