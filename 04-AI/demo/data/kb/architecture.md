# shop-app architecture

- Apache httpd 2.4 on port 443 terminates TLS and proxies to Tomcat with mod_proxy (127.0.0.1:8080, timeout 60 s).
- shop-app: Java 17, Spring Boot 3 on Tomcat 10, heap -Xmx2g, 40 request threads.
- Database: PostgreSQL 15 through HikariCP (maximumPoolSize 10, connectionTimeout 30000 ms).
- Payments: external gateway over HTTPS, read timeout 5 s.
- Logs: Apache access_log and error_log; application.log (logback); catalina.out (Tomcat); deploys.log (CI).
