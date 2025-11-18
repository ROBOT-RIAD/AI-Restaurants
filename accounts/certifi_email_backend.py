import ssl
import certifi
import smtplib
from django.core.mail.backends.smtp import EmailBackend as DjangoEmailBackend


class CertifiSMTPBackend(DjangoEmailBackend):
    """SMTP email backend that uses the certifi CA bundle for TLS.

    This fixes Windows installations that don't have a system CA bundle
    available to the Python ssl module and causes "certificate verify failed"
    errors during starttls().
    """

    def open(self):
        """Open a network connection and start TLS using certifi bundle if needed."""
        if self.connection:
            return False

        try:
            self.connection = smtplib.SMTP(self.host, self.port, timeout=self.timeout)
            # Identify to the SMTP server
            self.connection.ehlo()

            if self.use_tls:
                # Create SSLContext using certifi's CA bundle
                context = ssl.create_default_context(cafile=certifi.where())
                # Perform STARTTLS with our validated context
                self.connection.starttls(context=context)
                # Re-identify after STARTTLS
                self.connection.ehlo()

            if self.username and self.password:
                self.connection.login(self.username, self.password)

            return True
        except Exception:
            if self.fail_silently:
                return False
            raise
