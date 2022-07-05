package net.sourceforge.jvlt.ui.dialogs;

import java.awt.Dimension;
import java.awt.Frame;
import java.awt.GridBagConstraints;
import java.awt.GridBagLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.awt.event.KeyEvent;

import javax.swing.Action;
import javax.swing.JButton;
import javax.swing.JComponent;
import javax.swing.JDialog;
import javax.swing.JScrollPane;
import javax.swing.JTextArea;
import javax.swing.KeyStroke;

import net.sourceforge.jvlt.ui.utils.CustomConstraints;
import net.sourceforge.jvlt.ui.utils.GUIUtils;
import net.sourceforge.jvlt.utils.I18nService;

import org.apache.log4j.Level;
import org.apache.log4j.Logger;
import org.apache.log4j.PatternLayout;
import org.apache.log4j.WriterAppender;
import org.apache.log4j.spi.LoggingEvent;

public class ErrorLogDialog extends JDialog {
	private static final long serialVersionUID = 1L;

	final JTextArea _text_area = new JTextArea();

	public ErrorLogDialog(Frame parent) {
		super(parent, I18nService.getString("Labels", "error_log"), false);

		Logger.getRootLogger().addAppender(new TextAreaAppender());
		_text_area.setEditable(false);
		JScrollPane scrpane = new JScrollPane(_text_area);
		scrpane.setPreferredSize(new Dimension(400, 320));

		Action close_action = GUIUtils.createTextAction(new ActionListener() {
			public void actionPerformed(ActionEvent e) {
				setVisible(false);
			}
		}, "close");

		setLayout(new GridBagLayout());
		CustomConstraints cc = new CustomConstraints();
		cc.update(0, 0, 1.0, 1.0);
		getContentPane().add(scrpane, cc);
		cc.update(0, 1, 0.0, 0.0);
		cc.fill = GridBagConstraints.NONE;
		JButton closeButton = new JButton(close_action);
		closeButton.getActionMap().put("close", close_action);
		closeButton.getInputMap(JComponent.WHEN_IN_FOCUSED_WINDOW).put(
				KeyStroke.getKeyStroke(KeyEvent.VK_ESCAPE, 0), "close");
		getContentPane().add(closeButton, cc);
	}

	/**
	 * An appender writing to this dialog's text area.
	 * 
	 * @author thrar
	 */
	private class TextAreaAppender extends WriterAppender {

		/**
		 * Creates a new instance with default layout and WARN threshold.
		 */
		public TextAreaAppender() {
			setLayout(new PatternLayout("%d{HH:mm:ss} - %m%n"));
			setThreshold(Level.WARN);
		}

		@Override
		public void append(LoggingEvent event) {
			final String message = layout.format(event);
			_text_area.append(message);
		}
	}
}
