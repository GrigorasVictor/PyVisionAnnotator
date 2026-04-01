package annotation_server.annotation_service.support;

import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import io.jsonwebtoken.io.Decoders;
import io.jsonwebtoken.security.Keys;

import javax.crypto.SecretKey;
import java.time.Instant;
import java.util.Date;

public final class TestJwtFactory {

    private static final String SECRET = "dGVzdFNlY3JldEZvckFubm90YXRpb25TZXJ2aWNlVGVzdDEyMzQ1Njc4OTA=";

    private TestJwtFactory() {
    }

    public static String bearerFor(String userId) {
        SecretKey key = Keys.hmacShaKeyFor(Decoders.BASE64.decode(SECRET));
        Instant now = Instant.now();
        String token = Jwts.builder()
                .subject(userId)
                .issuedAt(Date.from(now))
                .expiration(Date.from(now.plusSeconds(3600)))
                .signWith(key, SignatureAlgorithm.HS256)
                .compact();
        return "Bearer " + token;
    }
}

