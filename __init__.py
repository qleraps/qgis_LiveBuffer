def classFactory(iface):
    from .livebuffer import LiveBufferPlugin
    return LiveBufferPlugin(iface)
