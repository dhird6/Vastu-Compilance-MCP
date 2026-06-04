using System;
using System.Collections.Generic;
using Autodesk.Revit.DB;
using Newtonsoft.Json.Linq;
using VastuRevitPlugin.Models;

namespace VastuRevitPlugin.Services;

internal static class RemediationParameterHelper
{
    public static bool TryGetPoint2D(
        RemediationAction action,
        string key,
        out double x,
        out double y)
    {
        x = 0;
        y = 0;
        if (!action.Parameters.TryGetValue(key, out object? raw) || raw == null)
        {
            return false;
        }

        if (raw is JObject json)
        {
            x = json["x"]?.Value<double>() ?? 0;
            y = json["y"]?.Value<double>() ?? 0;
            return true;
        }

        if (raw is Dictionary<string, object> dict)
        {
            x = Convert.ToDouble(dict.GetValueOrDefault("x", 0));
            y = Convert.ToDouble(dict.GetValueOrDefault("y", 0));
            return true;
        }

        return false;
    }

    public static bool TryGetTranslationFeet(RemediationAction action, out XYZ translation)
    {
        translation = XYZ.Zero;

        if (action.Parameters.TryGetValue("translation_feet", out object? raw) && raw != null)
        {
            if (raw is JObject json)
            {
                double x = json["x"]?.Value<double>() ?? 0;
                double y = json["y"]?.Value<double>() ?? 0;
                translation = new XYZ(x, y, 0);
                return translation.GetLength() > 1e-6;
            }
        }

        if (!TryGetShiftVector(action, out double dx, out double dy, out double distanceFeet))
        {
            return false;
        }

        translation = new XYZ(dx * distanceFeet, dy * distanceFeet, 0);
        return translation.GetLength() > 1e-6;
    }

    public static bool TryGetShiftVector(
        RemediationAction action,
        out double dx,
        out double dy,
        out double distanceFeet)
    {
        dx = 0;
        dy = 0;
        distanceFeet = 3.0;

        if (action.Parameters.TryGetValue("shift_distance_feet", out object? dist))
        {
            distanceFeet = Convert.ToDouble(dist);
        }

        if (!action.Parameters.TryGetValue("shift_vector", out object? raw) || raw == null)
        {
            return false;
        }

        if (raw is JObject json)
        {
            dx = json["dx"]?.Value<double>() ?? 0;
            dy = json["dy"]?.Value<double>() ?? 0;
            return true;
        }

        if (raw is Dictionary<string, object> dict)
        {
            dx = Convert.ToDouble(dict.GetValueOrDefault("dx", 0));
            dy = Convert.ToDouble(dict.GetValueOrDefault("dy", 0));
            return true;
        }

        return false;
    }

    public static double GetGuideLengthFeet(RemediationAction action, double defaultFeet = 3.0)
    {
        if (action.Parameters.TryGetValue("guide_length_feet", out object? value))
        {
            return Convert.ToDouble(value);
        }

        if (action.Parameters.TryGetValue("shift_distance_feet", out object? shift))
        {
            return Convert.ToDouble(shift);
        }

        return defaultFeet;
    }
}
