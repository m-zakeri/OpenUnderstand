package freemind.modes.mindmapmode;

import java.awt.*;
import java.awt.datatransfer.Clipboard;
import java.awt.datatransfer.Transferable;

public class MindMapController_Extracted1 {
    private Clipboard clipboard = null;
    private Clipboard selection = null;

    /**
     *
     */
    public Transferable getClipboardContents(MindMapController mindMapController) {
        getClipboard();
        return clipboard.getContents(mindMapController);
    }

    /**
     *
     */
    public void setClipboardContents(Transferable t) {
        getClipboard();
        clipboard.setContents(t, null);
        if (selection != null) {
            selection.setContents(t, null);
        }
    }

    public void getClipboard() {
        if (clipboard == null) {
            Toolkit toolkit = Toolkit.getDefaultToolkit();
            selection = toolkit.getSystemSelection();
            clipboard = toolkit.getSystemClipboard();

        }
    }
}