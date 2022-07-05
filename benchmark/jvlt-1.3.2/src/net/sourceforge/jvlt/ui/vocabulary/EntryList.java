package net.sourceforge.jvlt.ui.vocabulary;

import java.util.ArrayList;
import java.util.Collection;

import javax.swing.DefaultListModel;
import javax.swing.JList;

import net.sourceforge.jvlt.core.Entry;
import net.sourceforge.jvlt.core.Sense;

public class EntryList extends JList {
	private static final long serialVersionUID = 1L;

	private Collection<Entry> _entries;

	public EntryList() {
		super(new DefaultListModel());
		_entries = new ArrayList<Entry>();
	}

	public Collection<Entry> getEntries() {
		return _entries;
	}

	public void setEntries(Collection<Entry> entries) {
		_entries = entries;
		DefaultListModel model = (DefaultListModel) getModel();
		model.clear();
		for (Entry entry : entries) {
			model.addElement(getEntryString(entry));
		}
	}

	private String getEntryString(Entry entry) {
		StringBuffer buf = new StringBuffer();
		buf.append(entry.toString());
		buf.append(" - ");
		Sense[] senses = entry.getSenses();
		if (senses.length == 1) {
			buf.append(senses[0].toString());
		} else {
			for (int j = 0; j < senses.length; j++) {
				if (j > 0) {
					buf.append("; ");
				}

				buf.append(String.valueOf(j + 1) + ". ");
				buf.append(senses[j].toString());
			}
		}

		return buf.toString();
	}
}
