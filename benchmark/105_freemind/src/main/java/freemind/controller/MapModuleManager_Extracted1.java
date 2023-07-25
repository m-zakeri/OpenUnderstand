package freemind.controller;

import freemind.modes.ModeController;
import freemind.view.MapModule;

import java.util.*;

public class MapModuleManager_Extracted1 {
    /**
     * @return a map of String to MapModule elements.
     * @deprecated use getMapModuleVector instead (and get the displayname as
     * MapModule.getDisplayName().
     */
    public Map getMapModules(Vector thisMapModuleVector) {
        HashMap returnValue = new HashMap();
        for (Iterator iterator = thisMapModuleVector.iterator(); iterator.hasNext(); ) {
            MapModule module = (MapModule) iterator.next();
            returnValue.put(module.getDisplayName(), module);
        }
        return Collections.unmodifiableMap(returnValue);
    }

    public List getMapModuleVector(Vector thisMapModuleVector) {
        return Collections.unmodifiableList(thisMapModuleVector);
    }

    /**
     * @return an unmodifiable set of all display names of current opened maps.
     */
    public List getMapKeys(Vector thisMapModuleVector) {
        LinkedList returnValue = new LinkedList();
        for (Iterator iterator = thisMapModuleVector.iterator(); iterator.hasNext(); ) {
            MapModule module = (MapModule) iterator.next();
            returnValue.add(module.getDisplayName());
        }
        return Collections.unmodifiableList(returnValue);
    }

    public void addToOrChangeInMapModules(String key,
                                          MapModule newOrChangedMapModule, Vector thisMapModuleVector) {
        // begin bug fix, 20.12.2003, fc.
        // check, if already present:
        String extension = "";
        int count = 1;
        List mapKeys = getMapKeys(thisMapModuleVector);
        while (mapKeys.contains(key + extension)) {
            extension = "<" + (++count) + ">";
        }
        // rename map:
        newOrChangedMapModule.setName(key + extension);
        newOrChangedMapModule.setDisplayName(key + extension);
        if (!thisMapModuleVector.contains(newOrChangedMapModule)) {
            thisMapModuleVector.add(newOrChangedMapModule);
        }
        // end bug fix, 20.12.2003, fc.
    }

    public MapModule getModuleGivenModeController(ModeController pModeController, Vector thisMapModuleVector) {
        MapModule mapModule = null;
        for (Iterator iter = this.getMapModules(thisMapModuleVector).entrySet().iterator(); iter.hasNext(); ) {
            Map.Entry mapEntry = (Map.Entry) iter.next();
            mapModule = (MapModule) mapEntry.getValue();
            if (pModeController.equals(mapModule.getModeController())) {
                break;
            }
            mapModule = null;
        }
        return mapModule;
    }
}