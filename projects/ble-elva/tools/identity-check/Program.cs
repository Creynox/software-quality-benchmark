using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.Extensions.DependencyInjection;

// Controller only. Never export cookie contents, keys, stamps or claim collections.
try
{
    var request = JsonDocument.Parse(Console.In.ReadToEnd()).RootElement;
    var state = JsonDocument.Parse(File.ReadAllText(request.GetProperty("storage_state").GetString()!));
    var cookies = state.RootElement.GetProperty("cookies").EnumerateArray()
        .Where(c => c.GetProperty("domain").GetString() == "127.0.0.1" && c.GetProperty("path").GetString() == "/")
        .ToDictionary(c => c.GetProperty("name").GetString()!, c => c.GetProperty("value").GetString()!);
    const string name = ".AspNetCore.Identity.Application";
    var value = cookies[name];
    if (value.StartsWith("chunks:", StringComparison.Ordinal))
    {
        var count = int.Parse(value[7..]);
        if (count < 1 || count > 20) throw new InvalidOperationException();
        value = string.Concat(Enumerable.Range(1, count).Select(i => cookies[name + "C" + i]));
    }
    var services = new ServiceCollection();
    services.AddLogging();
    services.AddDataProtection().SetApplicationName(Path.GetFullPath(request.GetProperty("application_root").GetString()!).TrimEnd('\\') + "\\")
        .PersistKeysToFileSystem(new DirectoryInfo(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "ASP.NET", "DataProtection-Keys")))
        .DisableAutomaticKeyGeneration();
    using var provider = services.BuildServiceProvider();
    var protector = provider.GetRequiredService<IDataProtectionProvider>().CreateProtector(
        "Microsoft.AspNetCore.Authentication.Cookies.CookieAuthenticationMiddleware", "Identity.Application", "v2");
    var ticket = new TicketDataFormat(protector).Unprotect(value);
    if (ticket is null || ticket.Principal.Identity?.IsAuthenticated != true || ticket.Properties.IssuedUtc is null || ticket.Properties.IssuedUtc > DateTimeOffset.UtcNow
        || ticket.Properties.ExpiresUtc is null || ticket.Properties.ExpiresUtc <= DateTimeOffset.UtcNow) throw new InvalidOperationException();
    Console.WriteLine(JsonSerializer.Serialize(new { valid = true,
        username = ticket.Principal.FindFirstValue(ClaimTypes.Name), user_id = ticket.Principal.FindFirstValue(ClaimTypes.NameIdentifier),
        expires_utc = ticket.Properties.ExpiresUtc }));
    return 0;
}
catch
{
    Console.WriteLine("{\"valid\":false}");
    return 2;
}
