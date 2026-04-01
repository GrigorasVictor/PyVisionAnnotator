FROM maven:3.9-eclipse-temurin-21-alpine AS builder

WORKDIR /app

COPY pom.xml .
COPY src ./src

RUN mvn clean package -DskipTests

FROM eclipse-temurin:21-jre-alpine

WORKDIR /app

COPY --from=builder /app/target /app/target

# Pick the executable Spring Boot jar and normalize it to /app/app.jar.
RUN set -eux; \
	JAR_FILE="$(find /app/target -maxdepth 1 -type f -name '*.jar' ! -name '*.jar.original' | head -n 1)"; \
	test -n "$JAR_FILE"; \
	cp "$JAR_FILE" /app/app.jar

EXPOSE 8085

ENTRYPOINT ["java","-jar","/app/app.jar"]
