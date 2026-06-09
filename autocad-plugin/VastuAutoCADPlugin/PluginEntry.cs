using Autodesk.AutoCAD.Runtime;
using VastuAutoCADPlugin.Configuration;

namespace VastuAutoCADPlugin
{
    /// <summary>
    /// AutoCAD plugin entry point for Vastu Compliance MCP integration.
    /// </summary>
    public class PluginEntry : IExtensionApplication
    {
        public void Initialize()
        {
            var editor = Autodesk.AutoCAD.ApplicationServices.Application.DocumentManager.MdiActiveDocument?.Editor;
            editor?.WriteMessage(
                "\n[Vastu] Compliance plugin loaded v" + VastuPluginSettings.PluginVersion +
                " — MCP: " + VastuPluginSettings.BaseUrl);
        }

        public void Terminate()
        {
            // Plugin shutdown hook.
        }
    }
}
