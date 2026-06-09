using System.Collections.Generic;
using VastuAutoCADPlugin.Models;

namespace VastuAutoCADPlugin.Services
{
    public static class VastuSession
    {
        private static ComplianceReport _lastReport;
        private static GenerateLayoutFromReportResponse _lastGeneratedLayout;
        private static string _lastExportedDxfPath;
        private static string _lastHtmlReportPath;
        private static string _lastJsonReportPath;
        private static readonly List<UserLayoutConstraintDto> _layoutConstraints = new List<UserLayoutConstraintDto>();
        private static readonly List<string> _resultEntityHandles = new List<string>();
        private static readonly List<string> _generatedEntityHandles = new List<string>();

        public static void SetLastReport(ComplianceReport report)
        {
            _lastReport = report;
        }

        public static ComplianceReport GetLastReport()
        {
            return _lastReport;
        }

        public static void SetLastGeneratedLayout(GenerateLayoutFromReportResponse layout)
        {
            _lastGeneratedLayout = layout;
        }

        public static GenerateLayoutFromReportResponse GetLastGeneratedLayout()
        {
            return _lastGeneratedLayout;
        }

        public static void SetLastExportedDxfPath(string path)
        {
            _lastExportedDxfPath = path;
        }

        public static string GetLastExportedDxfPath()
        {
            return _lastExportedDxfPath;
        }

        public static void SetLastExportPaths(string htmlPath, string jsonPath)
        {
            _lastHtmlReportPath = htmlPath;
            _lastJsonReportPath = jsonPath;
        }

        public static string GetLastHtmlReportPath()
        {
            return _lastHtmlReportPath;
        }

        public static string GetLastJsonReportPath()
        {
            return _lastJsonReportPath;
        }

        public static IReadOnlyList<UserLayoutConstraintDto> GetLayoutConstraints()
        {
            return _layoutConstraints;
        }

        public static void AddLayoutConstraint(UserLayoutConstraintDto constraint)
        {
            if (constraint == null || string.IsNullOrWhiteSpace(constraint.ConstraintId))
            {
                return;
            }

            _layoutConstraints.RemoveAll(item => item.ConstraintId == constraint.ConstraintId);
            _layoutConstraints.Add(constraint);
        }

        public static void ClearLayoutConstraints()
        {
            _layoutConstraints.Clear();
        }

        public static void SetResultEntityHandles(IEnumerable<string> handles)
        {
            _resultEntityHandles.Clear();
            _resultEntityHandles.AddRange(handles);
        }

        public static IReadOnlyList<string> GetResultEntityHandles()
        {
            return _resultEntityHandles;
        }

        public static void ClearResultEntities()
        {
            _resultEntityHandles.Clear();
        }

        public static void SetGeneratedEntityHandles(IEnumerable<string> handles)
        {
            _generatedEntityHandles.Clear();
            _generatedEntityHandles.AddRange(handles);
        }

        public static IReadOnlyList<string> GetGeneratedEntityHandles()
        {
            return _generatedEntityHandles;
        }

        public static void ClearGeneratedEntities()
        {
            _generatedEntityHandles.Clear();
        }
    }
}
