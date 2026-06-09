using System;
using System.Net.Http;
using System.Text;
using Newtonsoft.Json;
using VastuAutoCADPlugin.Configuration;
using VastuAutoCADPlugin.Models;
using VastuAutoCADPlugin.Services.Abstractions;

namespace VastuAutoCADPlugin.Services
{
    /// <summary>
    /// Reusable HTTP client for Vastu Compliance REST API.
    /// </summary>
    public sealed class VastuApiClient : IVastuApiClient
    {
        private readonly string _baseUrl;

        public VastuApiClient()
            : this(VastuPluginSettings.BaseUrl)
        {
        }

        public VastuApiClient(string baseUrl)
        {
            _baseUrl = string.IsNullOrWhiteSpace(baseUrl)
                ? VastuPluginSettings.BaseUrl
                : baseUrl.TrimEnd('/');
        }

        public AnalyzeComplianceResponse AnalyzeAutocadLayout(AnalyzeAutocadRequest request)
        {
            return Post<AnalyzeAutocadRequest, AnalyzeComplianceResponse>(
                "/api/v1/compliance/analyze/autocad",
                request,
                VastuPluginSettings.AnalyzeTimeout,
                "AutoCAD analysis");
        }

        public GenerateLayoutFromReportResponse GenerateLayoutFromReport(GenerateLayoutFromReportRequest request)
        {
            return Post<GenerateLayoutFromReportRequest, GenerateLayoutFromReportResponse>(
                "/api/v1/layout/generate-from-report",
                request,
                VastuPluginSettings.GenerateLayoutTimeout,
                "Layout generation");
        }

        private TResponse Post<TRequest, TResponse>(string path, TRequest request, TimeSpan timeout, string operation)
        {
            string endpoint = _baseUrl + path;
            using (var client = new HttpClient())
            {
                client.Timeout = timeout;
                string payload = JsonConvert.SerializeObject(request);
                using (var content = new StringContent(payload, Encoding.UTF8, "application/json"))
                {
                    HttpResponseMessage response = client.PostAsync(endpoint, content).GetAwaiter().GetResult();
                    string body = response.Content.ReadAsStringAsync().GetAwaiter().GetResult();
                    if (!response.IsSuccessStatusCode)
                    {
                        throw new InvalidOperationException(
                            operation + " failed with status " + (int)response.StatusCode + ": " + body);
                    }

                    TResponse parsed = JsonConvert.DeserializeObject<TResponse>(body);
                    if (parsed == null)
                    {
                        throw new InvalidOperationException(operation + " returned an empty response.");
                    }

                    return parsed;
                }
            }
        }
    }
}
