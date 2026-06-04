using System;
using System.Net.Http;
using System.Text;
using Newtonsoft.Json;
using VastuAutoCADPlugin.Models;

namespace VastuAutoCADPlugin.Services
{
    public class VastuApiClient
    {
        private readonly string _baseUrl;

        public VastuApiClient()
        {
            string configured = Environment.GetEnvironmentVariable("VASTU_MCP_URL");
            _baseUrl = string.IsNullOrWhiteSpace(configured) ? "http://127.0.0.1:8000" : configured.TrimEnd('/');
        }

        public AnalyzeComplianceResponse AnalyzeAutocadLayout(AnalyzeAutocadRequest request)
        {
            string endpoint = _baseUrl + "/api/v1/compliance/analyze/autocad";
            using (var client = new HttpClient())
            {
                client.Timeout = TimeSpan.FromSeconds(60);
                string payload = JsonConvert.SerializeObject(request);
                using (var content = new StringContent(payload, Encoding.UTF8, "application/json"))
                {
                    HttpResponseMessage response = client.PostAsync(endpoint, content).GetAwaiter().GetResult();
                    string body = response.Content.ReadAsStringAsync().GetAwaiter().GetResult();
                    if (!response.IsSuccessStatusCode)
                    {
                        throw new InvalidOperationException(
                            "AutoCAD analysis failed with status " + (int)response.StatusCode + ": " + body
                        );
                    }
                    return JsonConvert.DeserializeObject<AnalyzeComplianceResponse>(body);
                }
            }
        }
    }
}
