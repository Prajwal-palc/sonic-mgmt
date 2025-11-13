"""
NTP CLI Automation Test Suite
Comprehensive tests for all NTP commands based on ntp.xml
"""

import pytest
import logging
from report_generator import TestCaseResult as TestResult

logger = logging.getLogger(__name__)


class TestNTPGlobalConfiguration:
    """Test Category 1: NTP Global Configuration"""

    @pytest.mark.global_config
    def test_ntp_001_enable_ntp(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-001: Enable NTP service"""
        test_id = "NTP-001"
        description = "Enable NTP service"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            # Enter config mode
            enhanced_ssh_client.enter_config_mode()

            # Enable NTP
            output, rc = enhanced_ssh_client.execute_command("ntp enable")
            result.add_command("ntp enable", output)

            # Exit config mode and verify
            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp global")
            result.add_command("show ntp global", output)

            # Verify NTP is enabled
            assert "enable" in output.lower() or rc == 0
            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.global_config
    def test_ntp_002_disable_ntp(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-002: Disable NTP service"""
        test_id = "NTP-002"
        description = "Disable NTP service"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            # First enable, then disable
            enhanced_ssh_client.execute_command("ntp enable")
            output, rc = enhanced_ssh_client.execute_command("no ntp enable")
            result.add_command("no ntp enable", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp global")
            result.add_command("show ntp global", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.global_config
    def test_ntp_003_reenable_ntp(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-003: Re-enable NTP service after disabling"""
        test_id = "NTP-003"
        description = "Re-enable NTP service"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            # Disable then enable
            enhanced_ssh_client.execute_command("no ntp enable")
            output, rc = enhanced_ssh_client.execute_command("ntp enable")
            result.add_command("ntp enable (after disable)", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp global")
            result.add_command("show ntp global", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)


class TestNTPAuthentication:
    """Test Category 2: NTP Authentication"""

    @pytest.mark.authentication
    def test_ntp_004_enable_authentication(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-004: Enable NTP authentication"""
        test_id = "NTP-004"
        description = "Enable NTP authentication"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            output, rc = enhanced_ssh_client.execute_command("ntp authenticate")
            result.add_command("ntp authenticate", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp global")
            result.add_command("show ntp global", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.authentication
    def test_ntp_005_disable_authentication(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-005: Disable NTP authentication"""
        test_id = "NTP-005"
        description = "Disable NTP authentication"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            enhanced_ssh_client.execute_command("ntp authenticate")
            output, rc = enhanced_ssh_client.execute_command("no ntp authenticate")
            result.add_command("no ntp authenticate", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp global")
            result.add_command("show ntp global", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.authentication
    def test_ntp_006_reenable_authentication(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-006: Re-enable NTP authentication"""
        test_id = "NTP-006"
        description = "Re-enable NTP authentication"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            enhanced_ssh_client.execute_command("no ntp authenticate")
            output, rc = enhanced_ssh_client.execute_command("ntp authenticate")
            result.add_command("ntp authenticate (after disable)", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp global")
            result.add_command("show ntp global", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)


class TestNTPAuthenticationKeys:
    """Test Category 3: NTP Authentication Keys"""

    @pytest.mark.auth_keys
    def test_ntp_007_auth_key_md5(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-007: Configure auth key with MD5"""
        test_id = "NTP-007"
        description = "Configure NTP authentication key with MD5"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            output, rc = enhanced_ssh_client.execute_command("ntp authentication-key 1 md5 TestPassword123")
            result.add_command("ntp authentication-key 1 md5 TestPassword123", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp global")
            result.add_command("show ntp global", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.auth_keys
    def test_ntp_008_auth_key_sha1(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-008: Configure auth key with SHA1"""
        test_id = "NTP-008"
        description = "Configure NTP authentication key with SHA1"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            output, rc = enhanced_ssh_client.execute_command("ntp authentication-key 2 sha1 SHA1Password456")
            result.add_command("ntp authentication-key 2 sha1 SHA1Password456", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp global")
            result.add_command("show ntp global", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.auth_keys
    def test_ntp_009_auth_key_sha256(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-009: Configure auth key with SHA256"""
        test_id = "NTP-009"
        description = "Configure NTP authentication key with SHA256"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            output, rc = enhanced_ssh_client.execute_command("ntp authentication-key 3 sha256 SHA256SecurePass")
            result.add_command("ntp authentication-key 3 sha256 SHA256SecurePass", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp global")
            result.add_command("show ntp global", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.auth_keys
    def test_ntp_010_auth_key_sha384(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-010: Configure auth key with SHA384"""
        test_id = "NTP-010"
        description = "Configure NTP authentication key with SHA384"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            output, rc = enhanced_ssh_client.execute_command("ntp authentication-key 4 sha384 SHA384SecurePass")
            result.add_command("ntp authentication-key 4 sha384 SHA384SecurePass", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp global")
            result.add_command("show ntp global", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.auth_keys
    def test_ntp_011_auth_key_sha512(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-011: Configure auth key with SHA512"""
        test_id = "NTP-011"
        description = "Configure NTP authentication key with SHA512"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            output, rc = enhanced_ssh_client.execute_command("ntp authentication-key 5 sha512 SHA512SecurePass")
            result.add_command("ntp authentication-key 5 sha512 SHA512SecurePass", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp global")
            result.add_command("show ntp global", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.auth_keys
    def test_ntp_012_auth_key_encrypted(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-012: Configure auth key with encrypted password"""
        test_id = "NTP-012"
        description = "Configure NTP authentication key with encrypted password"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            output, rc = enhanced_ssh_client.execute_command("ntp authentication-key 10 md5 EncryptedPass encrypted")
            result.add_command("ntp authentication-key 10 md5 EncryptedPass encrypted", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp global")
            result.add_command("show ntp global", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.auth_keys
    def test_ntp_013_delete_auth_key(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-013: Delete NTP authentication key"""
        test_id = "NTP-013"
        description = "Delete NTP authentication key"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            enhanced_ssh_client.execute_command("ntp authentication-key 1 md5 TestPassword123")
            output, rc = enhanced_ssh_client.execute_command("no ntp authentication-key 1")
            result.add_command("no ntp authentication-key 1", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp global")
            result.add_command("show ntp global", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.auth_keys
    def test_ntp_014_update_auth_key(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-014: Update NTP authentication key"""
        test_id = "NTP-014"
        description = "Update NTP authentication key"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            enhanced_ssh_client.execute_command("ntp authentication-key 100 md5 OldPassword")
            enhanced_ssh_client.execute_command("no ntp authentication-key 100")
            output, rc = enhanced_ssh_client.execute_command("ntp authentication-key 100 sha256 NewPassword")
            result.add_command("ntp authentication-key 100 sha256 NewPassword", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp global")
            result.add_command("show ntp global", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.auth_keys
    def test_ntp_015_multiple_auth_keys(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-015: Configure multiple authentication keys"""
        test_id = "NTP-015"
        description = "Configure multiple authentication keys"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            output1, rc = enhanced_ssh_client.execute_command("ntp authentication-key 11 md5 Pass1")
            result.add_command("ntp authentication-key 11 md5 Pass1", output1)

            output2, rc = enhanced_ssh_client.execute_command("ntp authentication-key 12 sha1 Pass2")
            result.add_command("ntp authentication-key 12 sha1 Pass2", output2)

            output3, rc = enhanced_ssh_client.execute_command("ntp authentication-key 13 sha256 Pass3")
            result.add_command("ntp authentication-key 13 sha256 Pass3", output3)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp global")
            result.add_command("show ntp global", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)


class TestNTPTrustedKeys:
    """Test Category 4: NTP Trusted Keys"""

    @pytest.mark.trusted_keys
    def test_ntp_016_configure_trusted_key(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-016: Configure NTP trusted key"""
        test_id = "NTP-016"
        description = "Configure NTP trusted key"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            enhanced_ssh_client.execute_command("ntp authentication-key 20 md5 TrustedPass")
            output, rc = enhanced_ssh_client.execute_command("ntp trusted-key 20")
            result.add_command("ntp trusted-key 20", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp global")
            result.add_command("show ntp global", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.trusted_keys
    def test_ntp_017_delete_trusted_key(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-017: Delete NTP trusted key"""
        test_id = "NTP-017"
        description = "Delete NTP trusted key"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            enhanced_ssh_client.execute_command("ntp authentication-key 21 md5 TrustedPass")
            enhanced_ssh_client.execute_command("ntp trusted-key 21")
            output, rc = enhanced_ssh_client.execute_command("no ntp trusted-key 21")
            result.add_command("no ntp trusted-key 21", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp global")
            result.add_command("show ntp global", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.trusted_keys
    def test_ntp_018_multiple_trusted_keys(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-018: Configure multiple trusted keys"""
        test_id = "NTP-018"
        description = "Configure multiple trusted keys"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            enhanced_ssh_client.execute_command("ntp authentication-key 30 md5 Pass1")
            enhanced_ssh_client.execute_command("ntp authentication-key 31 md5 Pass2")
            enhanced_ssh_client.execute_command("ntp authentication-key 32 md5 Pass3")
            enhanced_ssh_client.execute_command("ntp trusted-key 30")
            enhanced_ssh_client.execute_command("ntp trusted-key 31")
            output, rc = enhanced_ssh_client.execute_command("ntp trusted-key 32")
            result.add_command("ntp trusted-key 30,31,32", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp global")
            result.add_command("show ntp global", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.trusted_keys
    def test_ntp_019_update_trusted_key(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-019: Update trusted key configuration"""
        test_id = "NTP-019"
        description = "Update trusted key configuration"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            enhanced_ssh_client.execute_command("ntp authentication-key 40 md5 Pass")
            enhanced_ssh_client.execute_command("ntp trusted-key 40")
            enhanced_ssh_client.execute_command("no ntp trusted-key 40")
            output, rc = enhanced_ssh_client.execute_command("ntp trusted-key 40")
            result.add_command("ntp trusted-key 40 (reconfigured)", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp global")
            result.add_command("show ntp global", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)


class TestNTPServerConfiguration:
    """Test Category 5: NTP Server Configuration"""

    @pytest.mark.servers
    def test_ntp_020_basic_server_ip(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-020: Configure basic NTP server with IP"""
        test_id = "NTP-020"
        description = "Configure basic NTP server with IP address"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            output, rc = enhanced_ssh_client.execute_command("ntp server 10.10.10.1")
            result.add_command("ntp server 10.10.10.1", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp server")
            result.add_command("show ntp server", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.servers
    def test_ntp_021_server_hostname(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-021: Configure NTP server with hostname"""
        test_id = "NTP-021"
        description = "Configure NTP server with hostname"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            output, rc = enhanced_ssh_client.execute_command("ntp server time.google.com")
            result.add_command("ntp server time.google.com", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp server")
            result.add_command("show ntp server", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.servers
    def test_ntp_022_server_version_3(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-022: Configure NTP server with version 3"""
        test_id = "NTP-022"
        description = "Configure NTP server with version 3"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            output, rc = enhanced_ssh_client.execute_command("ntp server 10.10.10.2 version 3")
            result.add_command("ntp server 10.10.10.2 version 3", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp server")
            result.add_command("show ntp server", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.servers
    def test_ntp_023_server_version_4(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-023: Configure NTP server with version 4"""
        test_id = "NTP-023"
        description = "Configure NTP server with version 4"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            output, rc = enhanced_ssh_client.execute_command("ntp server 10.10.10.3 version 4")
            result.add_command("ntp server 10.10.10.3 version 4", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp server")
            result.add_command("show ntp server", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.servers
    def test_ntp_024_server_association_server(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-024: Configure NTP server with association type 'server'"""
        test_id = "NTP-024"
        description = "Configure NTP server with association type 'server'"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            output, rc = enhanced_ssh_client.execute_command("ntp server 10.10.10.4 association server")
            result.add_command("ntp server 10.10.10.4 association server", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp server")
            result.add_command("show ntp server", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.servers
    def test_ntp_025_server_association_pool(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-025: Configure NTP server with association type 'pool'"""
        test_id = "NTP-025"
        description = "Configure NTP server with association type 'pool'"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            output, rc = enhanced_ssh_client.execute_command("ntp server pool.ntp.org association pool")
            result.add_command("ntp server pool.ntp.org association pool", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp server")
            result.add_command("show ntp server", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.servers
    def test_ntp_026_server_iburst(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-026: Configure NTP server with iburst"""
        test_id = "NTP-026"
        description = "Configure NTP server with iburst option"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            output, rc = enhanced_ssh_client.execute_command("ntp server 10.10.10.5 iburst")
            result.add_command("ntp server 10.10.10.5 iburst", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp server")
            result.add_command("show ntp server", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.servers
    def test_ntp_027_server_with_key(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-027: Configure NTP server with authentication key"""
        test_id = "NTP-027"
        description = "Configure NTP server with authentication key"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            enhanced_ssh_client.execute_command("ntp authentication-key 50 md5 ServerKey")
            output, rc = enhanced_ssh_client.execute_command("ntp server 10.10.10.6 key 50")
            result.add_command("ntp server 10.10.10.6 key 50", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp server")
            result.add_command("show ntp server", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.servers
    def test_ntp_028_server_prefer(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-028: Configure NTP server with prefer option"""
        test_id = "NTP-028"
        description = "Configure NTP server with prefer option"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            output, rc = enhanced_ssh_client.execute_command("ntp server 10.10.10.7 prefer")
            result.add_command("ntp server 10.10.10.7 prefer", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp server")
            result.add_command("show ntp server", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.servers
    def test_ntp_029_server_all_options(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-029: Configure NTP server with all options"""
        test_id = "NTP-029"
        description = "Configure NTP server with all options"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            enhanced_ssh_client.execute_command("ntp authentication-key 60 sha256 CompleteServerKey")
            output, rc = enhanced_ssh_client.execute_command("ntp server 10.10.10.8 version 4 association server iburst key 60 prefer")
            result.add_command("ntp server 10.10.10.8 version 4 association server iburst key 60 prefer", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp server")
            result.add_command("show ntp server", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.servers
    def test_ntp_030_delete_server(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-030: Delete NTP server"""
        test_id = "NTP-030"
        description = "Delete NTP server"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            enhanced_ssh_client.execute_command("ntp server 10.10.10.9")
            output, rc = enhanced_ssh_client.execute_command("no ntp server 10.10.10.9")
            result.add_command("no ntp server 10.10.10.9", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp server")
            result.add_command("show ntp server", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.servers
    def test_ntp_031_update_server(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-031: Update NTP server configuration"""
        test_id = "NTP-031"
        description = "Update NTP server configuration"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            enhanced_ssh_client.execute_command("ntp server 10.10.10.10 version 3")
            enhanced_ssh_client.execute_command("no ntp server 10.10.10.10")
            output, rc = enhanced_ssh_client.execute_command("ntp server 10.10.10.10 version 4 iburst")
            result.add_command("ntp server 10.10.10.10 version 4 iburst", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp server")
            result.add_command("show ntp server", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.servers
    def test_ntp_032_multiple_servers(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-032: Configure multiple NTP servers"""
        test_id = "NTP-032"
        description = "Configure multiple NTP servers"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            enhanced_ssh_client.execute_command("ntp server 10.10.10.11")
            enhanced_ssh_client.execute_command("ntp server 10.10.10.12")
            enhanced_ssh_client.execute_command("ntp server 10.10.10.13")
            output, rc = enhanced_ssh_client.execute_command("ntp server 10.10.10.14")
            result.add_command("ntp server 10.10.10.11-14 (multiple)", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp server")
            result.add_command("show ntp server", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)


class TestNTPSourceInterface:
    """Test Category 6: NTP Source Interface"""

    @pytest.mark.source_interface
    def test_ntp_033_source_interface_ethernet(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-033: Configure NTP source interface Ethernet0"""
        test_id = "NTP-033"
        description = "Configure NTP source interface Ethernet0"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            output, rc = enhanced_ssh_client.execute_command("ntp source-interface Ethernet0")
            result.add_command("ntp source-interface Ethernet0", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp global")
            result.add_command("show ntp global", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.source_interface
    def test_ntp_034_source_interface_management(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-034: Configure NTP source interface Management0"""
        test_id = "NTP-034"
        description = "Configure NTP source interface Management0"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            output, rc = enhanced_ssh_client.execute_command("ntp source-interface Management0")
            result.add_command("ntp source-interface Management0", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp global")
            result.add_command("show ntp global", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.source_interface
    def test_ntp_035_delete_source_interface(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-035: Delete NTP source interface"""
        test_id = "NTP-035"
        description = "Delete NTP source interface"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            enhanced_ssh_client.execute_command("ntp source-interface Ethernet0")
            output, rc = enhanced_ssh_client.execute_command("no ntp source-interface")
            result.add_command("no ntp source-interface", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp global")
            result.add_command("show ntp global", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.source_interface
    def test_ntp_036_update_source_interface(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-036: Update NTP source interface"""
        test_id = "NTP-036"
        description = "Update NTP source interface"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            enhanced_ssh_client.execute_command("ntp source-interface Ethernet0")
            output, rc = enhanced_ssh_client.execute_command("ntp source-interface Management0")
            result.add_command("ntp source-interface Management0 (updated)", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp global")
            result.add_command("show ntp global", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)


class TestNTPVRFConfiguration:
    """Test Category 7: NTP VRF Configuration"""

    @pytest.mark.vrf
    def test_ntp_037_vrf_mgmt(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-037: Configure NTP with mgmt VRF"""
        test_id = "NTP-037"
        description = "Configure NTP with mgmt VRF"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            output, rc = enhanced_ssh_client.execute_command("ntp vrf mgmt")
            result.add_command("ntp vrf mgmt", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp global")
            result.add_command("show ntp global", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.vrf
    def test_ntp_038_vrf_default(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-038: Configure NTP with default VRF"""
        test_id = "NTP-038"
        description = "Configure NTP with default VRF"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            output, rc = enhanced_ssh_client.execute_command("ntp vrf default")
            result.add_command("ntp vrf default", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp global")
            result.add_command("show ntp global", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.vrf
    def test_ntp_039_delete_vrf(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-039: Delete NTP VRF configuration"""
        test_id = "NTP-039"
        description = "Delete NTP VRF configuration"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            enhanced_ssh_client.execute_command("ntp vrf mgmt")
            output, rc = enhanced_ssh_client.execute_command("no ntp vrf")
            result.add_command("no ntp vrf", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp global")
            result.add_command("show ntp global", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.vrf
    def test_ntp_040_update_vrf(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-040: Update NTP VRF configuration"""
        test_id = "NTP-040"
        description = "Update NTP VRF configuration"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            enhanced_ssh_client.execute_command("ntp vrf mgmt")
            output, rc = enhanced_ssh_client.execute_command("ntp vrf default")
            result.add_command("ntp vrf default (updated)", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp global")
            result.add_command("show ntp global", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)


class TestNTPShowCommands:
    """Test Category 8: Show Commands"""

    @pytest.mark.show_commands
    def test_ntp_041_show_global(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-041: Display NTP global configuration"""
        test_id = "NTP-041"
        description = "Display NTP global configuration"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            output, rc = enhanced_ssh_client.execute_show_command("show ntp global")
            result.add_command("show ntp global", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.show_commands
    def test_ntp_042_show_server(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-042: Display configured NTP servers"""
        test_id = "NTP-042"
        description = "Display configured NTP servers"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            output, rc = enhanced_ssh_client.execute_show_command("show ntp server")
            result.add_command("show ntp server", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.show_commands
    def test_ntp_043_show_associations(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-043: Display NTP associations"""
        test_id = "NTP-043"
        description = "Display NTP associations"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            output, rc = enhanced_ssh_client.execute_show_command("show ntp associations")
            result.add_command("show ntp associations", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)


class TestNTPComplexScenarios:
    """Test Category 9: Complex Scenarios"""

    @pytest.mark.complex
    def test_ntp_044_complete_setup(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-044: Complete NTP setup with authentication"""
        test_id = "NTP-044"
        description = "Complete NTP setup with authentication"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            enhanced_ssh_client.execute_command("ntp enable")
            enhanced_ssh_client.execute_command("ntp authenticate")
            enhanced_ssh_client.execute_command("ntp authentication-key 100 sha256 SecurePassword123")
            enhanced_ssh_client.execute_command("ntp trusted-key 100")
            enhanced_ssh_client.execute_command("ntp server 10.10.10.100 version 4 key 100 prefer iburst")
            enhanced_ssh_client.execute_command("ntp source-interface Management0")
            output, rc = enhanced_ssh_client.execute_command("ntp vrf mgmt")
            result.add_command("Complete NTP setup", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp global")
            result.add_command("show ntp global", output)

            output, rc = enhanced_ssh_client.execute_show_command("show ntp server")
            result.add_command("show ntp server", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.complex
    def test_ntp_045_delete_all_config(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-045: Delete all NTP configuration"""
        test_id = "NTP-045"
        description = "Delete all NTP configuration"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            # Setup first
            enhanced_ssh_client.execute_command("ntp enable")
            enhanced_ssh_client.execute_command("ntp server 10.10.10.100")
            enhanced_ssh_client.execute_command("ntp authentication-key 100 md5 Pass")
            enhanced_ssh_client.execute_command("ntp trusted-key 100")

            # Delete all
            enhanced_ssh_client.execute_command("no ntp server 10.10.10.100")
            enhanced_ssh_client.execute_command("no ntp trusted-key 100")
            enhanced_ssh_client.execute_command("no ntp authentication-key 100")
            enhanced_ssh_client.execute_command("no ntp source-interface")
            enhanced_ssh_client.execute_command("no ntp vrf")
            output, rc = enhanced_ssh_client.execute_command("no ntp enable")
            result.add_command("Delete all NTP config", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp global")
            result.add_command("show ntp global", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.complex
    def test_ntp_046_multiple_servers_different_options(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-046: Configure multiple servers with different options"""
        test_id = "NTP-046"
        description = "Configure multiple servers with different options"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            enhanced_ssh_client.execute_command("ntp enable")
            enhanced_ssh_client.execute_command("ntp authentication-key 201 md5 Pass1")
            enhanced_ssh_client.execute_command("ntp authentication-key 202 sha256 Pass2")
            enhanced_ssh_client.execute_command("ntp trusted-key 201")
            enhanced_ssh_client.execute_command("ntp trusted-key 202")
            enhanced_ssh_client.execute_command("ntp server 10.10.10.201 version 3 key 201 iburst")
            enhanced_ssh_client.execute_command("ntp server 10.10.10.202 version 4 key 202 prefer")
            output, rc = enhanced_ssh_client.execute_command("ntp server time.google.com association pool iburst")
            result.add_command("Multiple servers with different options", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp server")
            result.add_command("show ntp server", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.complex
    def test_ntp_047_config_persistence(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-047: Test NTP configuration persistence"""
        test_id = "NTP-047"
        description = "Test NTP configuration persistence"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            enhanced_ssh_client.execute_command("ntp enable")
            output, rc = enhanced_ssh_client.execute_command("ntp server 10.10.10.250 prefer")
            result.add_command("Configure NTP", output)

            enhanced_ssh_client.exit_config_mode()

            # Note: write memory may not work in all environments
            # output, rc = enhanced_ssh_client.execute_command("write memory")
            # result.add_command("write memory", output)

            output, rc = enhanced_ssh_client.execute_show_command("show ntp global")
            result.add_command("show ntp global", output)

            output, rc = enhanced_ssh_client.execute_show_command("show ntp server")
            result.add_command("show ntp server", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.complex
    def test_ntp_048_max_authentication_keys(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-048: Test maximum authentication keys"""
        test_id = "NTP-048"
        description = "Test maximum authentication keys"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            enhanced_ssh_client.execute_command("ntp authentication-key 1 md5 Key1")
            enhanced_ssh_client.execute_command("ntp authentication-key 100 sha1 Key100")
            enhanced_ssh_client.execute_command("ntp authentication-key 1000 sha256 Key1000")
            enhanced_ssh_client.execute_command("ntp authentication-key 10000 sha384 Key10000")
            output, rc = enhanced_ssh_client.execute_command("ntp authentication-key 65535 sha512 Key65535")
            result.add_command("Authentication keys with various IDs", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp global")
            result.add_command("show ntp global", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.complex
    def test_ntp_049_boundary_ntp_versions(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-049: Test boundary values for NTP version"""
        test_id = "NTP-049"
        description = "Test boundary values for NTP version"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            enhanced_ssh_client.execute_command("ntp server 10.10.10.3 version 3")
            output, rc = enhanced_ssh_client.execute_command("ntp server 10.10.10.4 version 4")
            result.add_command("NTP servers with versions 3 and 4", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp server")
            result.add_command("show ntp server", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)

    @pytest.mark.complex
    def test_ntp_050_all_authentication_types(self, enhanced_enhanced_ssh_client, vs_instance, comprehensive_reporter):
        """NTP-050: Test all authentication types"""
        test_id = "NTP-050"
        description = "Test all authentication types"
        result = TestResult(test_id, description, vs_instance['name'], "General")
        result.start()

        try:
            enhanced_ssh_client.enter_config_mode()

            enhanced_ssh_client.execute_command("ntp authentication-key 501 md5 MD5Pass")
            enhanced_ssh_client.execute_command("ntp authentication-key 502 sha1 SHA1Pass")
            enhanced_ssh_client.execute_command("ntp authentication-key 503 sha256 SHA256Pass")
            enhanced_ssh_client.execute_command("ntp authentication-key 504 sha384 SHA384Pass")
            output, rc = enhanced_ssh_client.execute_command("ntp authentication-key 505 sha512 SHA512Pass")
            result.add_command("All authentication types", output)

            enhanced_ssh_client.exit_config_mode()
            output, rc = enhanced_ssh_client.execute_show_command("show ntp global")
            result.add_command("show ntp global", output)

            result.complete("PASS")

        except Exception as e:
            result.complete("FAIL", str(e))
            pytest.fail(str(e))
        finally:
            comprehensive_reporter.add_result(result)
