import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Base64;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.net.URLEncoder;

public class Demo {
    private static final String API_URL = System.getenv().getOrDefault("API_URL", "http://127.0.0.1:8080");
    private static final String KEY_ID = System.getenv().getOrDefault("API_KEY_ID", "72b0b0aa-ad82-4182-a631-ae4865e8ae0e");
    private static final String KEY_SECRET = System.getenv().getOrDefault("API_KEY_SECRET", "6fuSO7P1m4cj8SSlgaYdblOjNAmnxDVD7tr8");
    private static final String ORG_ID = System.getenv().getOrDefault("ORG_ID", "00000000-0000-0000-0000-000000000002");

    public static void main(String[] args) throws Exception {
        APIClient client = new APIClient();
        String result = client.getAccountSecret("ubuntu_docker", "root");
        System.out.println(result);
    }

    static class APIClient {
        private final HttpClient httpClient = HttpClient.newHttpClient();

        public String getAccountSecret(String asset, String account) throws Exception {
            // Encode URL parameters
            String queryString = "asset=" + URLEncoder.encode(asset, StandardCharsets.UTF_8) +
                                 "&account=" + URLEncoder.encode(account, StandardCharsets.UTF_8);

            // Complete URL with parameters
            String url = API_URL + "/api/v1/accounts/integration-applications/account-secret/?" + queryString;

            // Get the current UTC time
            String date = ZonedDateTime.now().format(DateTimeFormatter.RFC_1123_DATE_TIME);

            // Build (request-target), including query parameters
            String requestTarget = "get /api/v1/accounts/integration-applications/account-secret/?" + queryString;

            // Generate the signing string
            String signingString = "(request-target): " + requestTarget + "\n" +
                                   "accept: application/json\n" +
                                   "date: " + date + "\n" +
                                   "x-jms-org: " + ORG_ID;
            String signature = sign(signingString, KEY_SECRET);

            // Build the HTTP request
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(url))
                    .header("Accept", "application/json")
                    .header("Date", date)
                    .header("X-JMS-ORG", ORG_ID)
                    .header("X-Source", "jms-pam")
                    .header("Authorization", "Signature keyId=\"" + KEY_ID + "\",algorithm=\"hmac-sha256\",headers=\"(request-target) accept date x-jms-org\",signature=\"" + signature + "\"")
                    .build();

            // Send the request
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() == 200) {
                return response.body();
            } else {
                System.err.println("API request failed: " + response.statusCode());
                return null;
            }
        }

        // Calculate the HMAC-SHA256 signature
        private String sign(String data, String key) throws Exception {
            Mac mac = Mac.getInstance("HmacSHA256");
            SecretKeySpec secretKeySpec = new SecretKeySpec(key.getBytes(StandardCharsets.UTF_8), "HmacSHA256");
            mac.init(secretKeySpec);
            byte[] rawHmac = mac.doFinal(data.getBytes(StandardCharsets.UTF_8));
            return Base64.getEncoder().encodeToString(rawHmac);
        }
    }
}
