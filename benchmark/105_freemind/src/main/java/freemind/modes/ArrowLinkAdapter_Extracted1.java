package freemind.modes;

public class ArrowLinkAdapter_Extracted1 implements Cloneable {
    private String startArrow;
    private String endArrow;

    public String getStartArrow() {
        return startArrow;
    }

    public void setStartArrow2(String startArrow) {
        this.startArrow = startArrow;
    }

    public String getEndArrow() {
        return endArrow;
    }

    public void setEndArrow2(String endArrow) {
        this.endArrow = endArrow;
    }

    public void setStartArrow(String startArrow) {
        if (startArrow == null || startArrow.toUpperCase().equals("NONE")) {
            this.startArrow = "None";
            return;
        } else if (startArrow.toUpperCase().equals("DEFAULT")) {
            this.startArrow = "Default";
            return;
        }
        // dont change:
        System.err.println("Cannot set the start arrow type to " + startArrow);
    }

    public void setEndArrow(String endArrow) {
        if (endArrow == null || endArrow.toUpperCase().equals("NONE")) {
            this.endArrow = "None";
            return;
        } else if (endArrow.toUpperCase().equals("DEFAULT")) {
            this.endArrow = "Default";
            return;
        }
        // dont change:
        System.err.println("Cannot set the end arrow type to " + endArrow);
    }

    public Object clone() throws CloneNotSupportedException {
        return (ArrowLinkAdapter_Extracted1) super.clone();
    }
}