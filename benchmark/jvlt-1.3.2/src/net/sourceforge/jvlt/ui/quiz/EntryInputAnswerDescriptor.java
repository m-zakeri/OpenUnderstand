package net.sourceforge.jvlt.ui.quiz;

import java.awt.GridBagLayout;

import javax.swing.JLabel;
import javax.swing.JPanel;

import net.sourceforge.jvlt.event.SelectionNotifier;
import net.sourceforge.jvlt.quiz.QueryResult;
import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.utils.I18nService;

class EntryInputAnswerDescriptor extends EntryDescriptor {
	private JLabel _answer_label;

	public EntryInputAnswerDescriptor(QuizModel m, SelectionNotifier n) {
		super(m, n);
	}

	@Override
	public String getID() {
		return "entry_input_answer";
	}

	public void setResult(QueryResult result) {
		String text = "";
		if (result != null) {
			String answer = result.getAnswer();
			if (result.isKnown()) {
				text = I18nService.getString("Messages", "answer_correct",
						new String[] { answer });
			} else { // ! result.isKnown()
				if (answer == null) {
					text = I18nService.getString("Messages", "no_answer");
				} else {
					text = I18nService.getString("Messages", "answer_wrong",
							new String[] { answer });
				}
			}
		}

		_answer_label.setText(text);
	}

	@Override
	protected void init() {
		_answer_label = new JLabel();

		_panel = new JPanel();
		_panel.setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1.0, 1.0);
		_panel.add(_info_panel, cc);
		cc.update(0, 1, 1.0, 0.0);
		_panel.add(_flag_panel, cc);
		cc.update(0, 2, 1.0, 0.0);
		_panel.add(_answer_label, cc);
	}
}
