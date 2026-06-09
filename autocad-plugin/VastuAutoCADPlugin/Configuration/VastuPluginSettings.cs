using System;

namespace VastuAutoCADPlugin.Configuration
{
    /// <summary>
    /// Centralized plugin configuration loaded from environment variables.
    /// </summary>
    public static class VastuPluginSettings
    {
        private const string DefaultBaseUrl = "http://127.0.0.1:8000";

        public static string BaseUrl =>
            NormalizeBaseUrl(Environment.GetEnvironmentVariable("VASTU_MCP_URL"));

        public static string ReportsFolderName => "VastuReports";

        public static TimeSpan AnalyzeTimeout => TimeSpan.FromSeconds(60);

        public static TimeSpan GenerateLayoutTimeout => TimeSpan.FromSeconds(120);

        public static string PluginVersion => "1.0.0";

        private static string NormalizeBaseUrl(string configured)
        {
            if (string.IsNullOrWhiteSpace(configured))
            {
                return DefaultBaseUrl;
            }

            return configured.TrimEnd('/');
        }
    }
}
