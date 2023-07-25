package accessories.plugins.time;

import javax.swing.*;
import java.awt.*;
import java.util.Calendar;
import java.util.Date;

public class TimeManagement_Extracted1 {
    private JPanel timePanel;
    private JTextField hourField;
    private JTextField minuteField;

    /**
     *
     */
    public JPanel getTimePanel(JTripleCalendar thisCalendar, TimeManagement timeManagement) {
        if (timePanel == null) {
            timePanel = new JPanel();
            timePanel.setLayout(new GridBagLayout());
            {
                GridBagConstraints gb2 = new GridBagConstraints();
                gb2.gridx = 0;
                gb2.gridy = 0;
                gb2.fill = GridBagConstraints.HORIZONTAL;
                timePanel.add(new JLabel(
                                timeManagement.getResourceString("plugins/TimeManagement.xml_hour")),
                        gb2);
            }
            {
                GridBagConstraints gb2 = new GridBagConstraints();
                gb2.gridx = 1;
                gb2.gridy = 0;
                gb2.fill = GridBagConstraints.HORIZONTAL;
                hourField = new JTextField(2);
                hourField.setText(new Integer(thisCalendar.getCalendar().get(
                        Calendar.HOUR_OF_DAY)).toString());
                timePanel.add(hourField, gb2);
            }
            {
                GridBagConstraints gb2 = new GridBagConstraints();
                gb2.gridx = 2;
                gb2.gridy = 0;
                gb2.fill = GridBagConstraints.HORIZONTAL;
                timePanel
                        .add(new JLabel(
                                        timeManagement.getResourceString("plugins/TimeManagement.xml_minute")),
                                gb2);
            }
            {
                GridBagConstraints gb2 = new GridBagConstraints();
                gb2.gridx = 3;
                gb2.gridy = 0;
                gb2.fill = GridBagConstraints.HORIZONTAL;
                minuteField = new JTextField(2);
                String minuteString = new Integer(thisCalendar.getCalendar().get(
                        Calendar.MINUTE)).toString();
                // padding with "0"
                if (minuteString.length() < 2) {
                    minuteString = "0" + minuteString;
                }
                minuteField.setText(minuteString);
                timePanel.add(minuteField, gb2);
            }

        }
        return timePanel;
    }

    /**
     *
     */
    public Date getCalendarDate(JTripleCalendar thisCalendar) {
        Calendar cal = thisCalendar.getCalendar();
        try {
            int value = 0;
            value = Integer.parseInt(hourField.getText());
            cal.set(Calendar.HOUR_OF_DAY, value);
            value = Integer.parseInt(minuteField.getText());
            cal.set(Calendar.MINUTE, value);
            cal.set(Calendar.SECOND, 0);
        } catch (Exception e) {
        }
        return cal.getTime();
    }
}