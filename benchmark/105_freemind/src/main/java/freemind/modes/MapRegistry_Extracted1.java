package freemind.modes;

import freemind.controller.filter.util.SortedMapListModel;

import java.util.Iterator;
import java.util.List;
import java.util.ListIterator;

public class MapRegistry_Extracted1 {
    private SortedMapListModel mapIcons;

    public SortedMapListModel getMapIcons() {
        return mapIcons;
    }

    public void setMapIcons(SortedMapListModel mapIcons) {
        this.mapIcons = mapIcons;
    }

    public void addIcon(MindIcon icon) {
        mapIcons.add(icon);
    }

    public void registryNodeIcons(MindMapNode node) {
        List icons = node.getIcons();
        Iterator i = icons.iterator();
        while (i.hasNext()) {
            MindIcon icon = (MindIcon) i.next();
            addIcon(icon);
        }
    }

    public void registrySubtree(MindMapNode root, boolean registerMyself, MapRegistry mapRegistry) {
        if (registerMyself) {
            registryNodeIcons(root);
            mapRegistry.registryAttributes(root);
        }
        ListIterator iterator = root.childrenUnfolded();
        while (iterator.hasNext()) {
            MindMapNode node = (MindMapNode) iterator.next();
            registrySubtree(node, true, mapRegistry);
        }
    }
}