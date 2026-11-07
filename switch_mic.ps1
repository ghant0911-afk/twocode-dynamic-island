$code = @'
using System;
using System.Runtime.InteropServices;

[ComImport]
[Guid("870af99c-171d-4f9e-af0d-e63df40c2bc9")]
public class PolicyConfigClient {}

[Guid("f8679f50-850a-41cf-9c72-430f290290c8")]
[InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IPolicyConfig
{
    [PreserveSig] int GetMixFormat(string pszDeviceName, IntPtr ppFormat);
    [PreserveSig] int GetDeviceFormat(string pszDeviceName, bool bDefault, IntPtr ppFormat);
    [PreserveSig] int ResetDeviceFormat(string pszDeviceName);
    [PreserveSig] int SetDeviceFormat(string pszDeviceName, IntPtr pEndpointFormat, IntPtr pMixFormat);
    [PreserveSig] int GetProcessingPeriod(string pszDeviceName, bool bDefault, IntPtr pmftDefaultPeriod, IntPtr pmftMinimumPeriod);
    [PreserveSig] int SetProcessingPeriod(string pszDeviceName, IntPtr pmftPeriod);
    [PreserveSig] int GetShareMode(string pszDeviceName, IntPtr pMode);
    [PreserveSig] int SetShareMode(string pszDeviceName, IntPtr mode);
    [PreserveSig] int GetPropertyValue(string pszDeviceName, bool bFxStore, IntPtr key, IntPtr pv);
    [PreserveSig] int SetPropertyValue(string pszDeviceName, bool bFxStore, IntPtr key, IntPtr pv);
    [PreserveSig] int SetDefaultEndpoint(string pszDeviceName, int role);
    [PreserveSig] int SetEndpointVisibility(string pszDeviceName, bool bVisible);
}

public class AudioSwitcher
{
    public static void SetDefault(string devId)
    {
        var client = (IPolicyConfig)new PolicyConfigClient();
        client.SetDefaultEndpoint(devId, 0);
        client.SetDefaultEndpoint(devId, 1);
        client.SetDefaultEndpoint(devId, 2);
    }
}
'@

Add-Type -TypeDefinition $code -Language CSharp
$realMicId = "{0.0.1.00000000}.{4bb65a9e-fea9-44f7-bd0c-53b98f7a87a5}"
[AudioSwitcher]::SetDefault($realMicId)
Write-Host "SUCCESS: Real Microphone set as default!"
