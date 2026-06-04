using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text;
using Newtonsoft.Json;
using VastuRevitPlugin.Models;

namespace VastuRevitPlugin.Services;

public class VastuApiClient
{
    private readonly string _baseUrl;

    public VastuApiClient()
    {
        string? configured = Environment.GetEnvironmentVariable("VASTU_MCP_URL");
        _baseUrl = string.IsNullOrWhiteSpace(configured) ? "http://127.0.0.1:8000" : configured.TrimEnd('/');
    }

    public AnalyzeComplianceResponse AnalyzeRevit3D(RevitAnalyzeRequest request)
    {
        return Post<AnalyzeComplianceResponse>("/api/v1/compliance/analyze/revit3d", request);
    }

    public AnalyzeComplianceResponse AnalyzeRevit3DDelta(RevitAnalyzeRequest request, List<string> roomIds)
    {
        var body = new
        {
            payload = request.Payload,
            context = request.Context,
            room_ids = roomIds
        };
        return Post<AnalyzeComplianceResponse>("/api/v1/compliance/analyze/revit3d/delta", body);
    }

    private T Post<T>(string path, object request)
    {
        string endpoint = _baseUrl + path;
        using var httpClient = new HttpClient();
        httpClient.Timeout = TimeSpan.FromSeconds(60);
        string json = JsonConvert.SerializeObject(request);
        using var content = new StringContent(json, Encoding.UTF8, "application/json");
        HttpResponseMessage response = httpClient.PostAsync(endpoint, content).GetAwaiter().GetResult();
        string responseBody = response.Content.ReadAsStringAsync().GetAwaiter().GetResult();
        if (!response.IsSuccessStatusCode)
        {
            throw new InvalidOperationException(
                "Vastu MCP request failed with status " + (int)response.StatusCode + ": " + responseBody);
        }

        T? result = JsonConvert.DeserializeObject<T>(responseBody);
        if (result == null)
        {
            throw new InvalidOperationException("Empty response from Vastu MCP server.");
        }

        return result;
    }
}
