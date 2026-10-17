using System.Text.Json;
using Microsoft.AspNetCore.Identity;

// Controller IPC only; stdout must be captured privately, never forwarded/logged.
// No source account/password/hash lookup, database, file or network operations.
try
{
    var input = JsonDocument.Parse(Console.In.ReadToEnd()).RootElement;
    var username = input.GetProperty("username").GetString()!;
    var allowed = new[] { "sqbf-labormitarbeiter", "sqbf-wpk", "sqbf-werkleitung" };
    if (!allowed.Contains(username)) throw new InvalidOperationException();
    var password = input.GetProperty("password").GetString()!;
    if (password.Length < 24 || password.Length > 128) throw new InvalidOperationException();
    var user = new IdentityUser<Guid> { Id = Guid.NewGuid(), UserName = username };
    var hasher = new PasswordHasher<IdentityUser<Guid>>();
    if (input.TryGetProperty("synthetic_hash_to_verify", out var candidate))
    {
        var verified = hasher.VerifyHashedPassword(user, candidate.GetString()!, password)
            != PasswordVerificationResult.Failed;
        Console.WriteLine(JsonSerializer.Serialize(new { verified }));
        return verified ? 0 : 2;
    }
    var hash = hasher.HashPassword(user, password);
    if (hasher.VerifyHashedPassword(user, hash, password) == PasswordVerificationResult.Failed)
        throw new InvalidOperationException();
    Console.WriteLine(JsonSerializer.Serialize(new { password_hash = hash }));
    return 0;
}
catch
{
    Console.WriteLine("{\"status\":\"BLOCKED_SYNTHETIC_PASSWORD\"}");
    return 2;
}
