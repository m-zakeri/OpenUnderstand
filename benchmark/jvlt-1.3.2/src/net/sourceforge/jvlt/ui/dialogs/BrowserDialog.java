package net.sourceforge.jvlt.ui.dialogs;

import java.awt.Dimension;
import java.awt.Frame;
import java.awt.GridBagLayout;
import java.awt.GridLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.io.IOException;
import java.net.URL;
import java.util.ArrayList;
import java.util.List;

import javax.swing.Action;
import javax.swing.JButton;
import javax.swing.JDialog;
import javax.swing.JEditorPane;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.SwingConstants;
import javax.swing.event.HyperlinkEvent;
import javax.swing.event.HyperlinkListener;

import net.sourceforge.jvlt.ui.components.ButtonPanel;
import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.ui.utils.GUIUtils;
import net.sourceforge.jvlt.utils.I18nService;

import org.apache.log4j.Logger;

public class BrowserDialog extends JDialog {
	private static final long serialVersionUID = 1L;

	private final Browser _browser;

	public BrowserDialog(Frame owner, URL page) {
		super(owner, I18nService.getString("Labels", "help"), false);

		_browser = new Browser();
		_browser.setPage(page);
		getContentPane().setLayout(new GridLayout());
		getContentPane().add(_browser);
	}
}

class Browser extends JPanel {
	private static final Logger logger = Logger.getLogger(Browser.class);

	class LinkFollower implements HyperlinkListener {
		public void hyperlinkUpdate(HyperlinkEvent ev) {
			if (ev.getEventType() == HyperlinkEvent.EventType.ACTIVATED) {
				_history.add(ev.getURL());
				_history_index = _history.size() - 1;
				update();
			}
		}
	}

	class ActionEventHandler implements ActionListener {
		public void actionPerformed(ActionEvent ev) {
			if (ev.getActionCommand().equals("back")) {
				_history_index--;
				update();
			} else if (ev.getActionCommand().equals("forward")) {
				_history_index++;
				update();
			}
		}
	}

	private static final long serialVersionUID = 1L;

	private final List<URL> _history;
	private int _history_index;

	private Action _back_action;
	private Action _forward_action;
	private JEditorPane _html_pane;

	public Browser() {
		_history = new ArrayList<URL>();
		_history_index = -1;

		init();
	}

	public void setPage(URL url) {
		_history.clear();
		_history.add(url);
		_history_index = 0;
		update();
	}

	private void init() {
		_back_action = GUIUtils.createIconAction(new ActionEventHandler(),
				"back");
		_forward_action = GUIUtils.createIconAction(new ActionEventHandler(),
				"forward");
		ButtonPanel button_panel = new ButtonPanel(SwingConstants.HORIZONTAL,
				SwingConstants.LEFT);
		button_panel.addButton(new JButton(_back_action));
		button_panel.addButton(new JButton(_forward_action));

		_html_pane = new JEditorPane();
		_html_pane.setEditable(false);
		_html_pane.setContentType("text/html");
		_html_pane.addHyperlinkListener(new LinkFollower());
		JScrollPane scrpane = new JScrollPane(_html_pane);
		scrpane.setPreferredSize(new Dimension(640, 480));

		setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1.0, 0.0);
		add(button_panel, cc);
		cc.update(0, 1, 1.0, 1.0);
		add(scrpane, cc);
	}

	private void update() {
		_back_action.setEnabled(_history_index > 0);
		_forward_action.setEnabled(_history_index < _history.size() - 1);
		try {
			URL url = _history.get(_history_index);
			_html_pane.setPage(url);
		} catch (IOException ex) {
			logger.error(ex);
		}
	}
}
