package freemind.modes.mindmapmode;

import freemind.modes.mindmapmode.MindMapController.MindMapControllerPlugin;

import java.util.Collections;
import java.util.HashSet;
import java.util.Set;

public class MindMapController_Extracted2 {
    /**
     * A general list of MindMapControllerPlugin s. Members need to be tested
     * for the right class and casted to be applied.
     */
    private HashSet mPlugins = new HashSet();

    public HashSet getMPlugins() {
        return mPlugins;
    }

    public void deregisterPlugin(MindMapControllerPlugin pPlugin) {
        mPlugins.remove(pPlugin);
    }

    public Set getPlugins() {
        return Collections.unmodifiableSet(mPlugins);
    }
}