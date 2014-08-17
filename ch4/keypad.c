/* -*- mode: c; c-file-style: "gnu" -*- */
/*
 * The code is free and can be used for any purpose including commercial
 * purposes.  Packt Publishing and the authors can not be held liable for
 * any use or result of the book's text or code.  Further copyright &
 * license info is found in the book's Copyright page.  The book can be
 * obtained from
 * "https://www.packtpub.com/hardware-and-creative/beaglebone-secret-agents".
*/
#include <errno.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <linux/i2c-dev.h>
#include <sys/ioctl.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <stdbool.h>

#include <tss/tss_error.h>
#include <tss/platform.h>
#include <tss/tss_defines.h>
#include <tss/tss_typedef.h>
#include <tss/tss_structs.h>
#include <tss/tspi.h>
#include <trousers/trousers.h>


#define DEBUG 1
/* TPM Debug */
#define DBG(message,tResult) if(DEBUG) {                        \
        printf("(Line %d, %s) %s returned 0x%08x. %s.\n",       \
               __LINE__,                                        \
               __func__,                                        \
               message,                                         \
               tResult,                                         \
               Trspi_Error_String(tResult));                    \
    }


TSS_RESULT extend_pcr (const char * buf, const int len)
{

    TSS_HCONTEXT hContext=0;
    TSS_HTPM hTPM = 0;
    TSS_RESULT result;
    TSS_HKEY hSRK = 0;
    TSS_HPOLICY hSRKPolicy=0;
    TSS_HPOLICY hOwnerPolicy=0;
    TSS_UUID SRK_UUID = TSS_UUID_SRK;
    BYTE passcode[20];

    memset(passcode,0,20);
    memcpy (passcode, buf, len);

    UINT32 ulNewPcrValueLength;
    BYTE* NewPcrValue;

    result = Tspi_Context_Create (&hContext);

    DBG(" Create a Context\n",result);
    result = Tspi_Context_Connect (hContext, NULL);
    DBG(" Connect to TPM\n", result);

    // Get the TPM handle
    result = Tspi_Context_GetTpmObject (hContext, &hTPM);
    DBG(" Get TPM Handle\n",result);

    result = Tspi_GetPolicyObject (hTPM, TSS_POLICY_USAGE, &hOwnerPolicy);
    DBG( " Owner Policy\n", result);

    result = Tspi_TPM_PcrExtend (hTPM,
                                 9,
                                 sizeof(passcode),
                                 passcode,
                                 NULL,
                                 &ulNewPcrValueLength,
                                 &NewPcrValue);

    DBG(" extend\n",result);

    return result;
}

bool get_code (char * buf, const int len)
{
  int fd;
  char *filename = "/dev/i2c-1";
  const int addr = 0x42;
  bool result = false;

  if ((fd = open (filename, O_RDWR)) < 0)
    {
      perror ("Failed to open the i2c bus");
      exit (EXIT_FAILURE);
    }


  if (ioctl(fd, I2C_SLAVE, addr) < 0)
    {
      perror ("Failed to acquire bus access and/or talk to slave.\n");
      close (fd);
      exit (EXIT_FAILURE);
    }

  const char * cmd = "HI";

  if ((write(fd, cmd, strlen(cmd))) < 0)
    {
      perror ("Failed to write to device");
      close (fd);
      exit (EXIT_FAILURE);
    }

  /* Wait for pin entry */
  sleep (10);

  if (read(fd,buf,len ) != len)
    {
      perror ("Failed to read from the i2c bus: %s.\n");
      printf("\n\n");
    }
  else
    {
#ifdef DEBUG
      int x = 0;
      for (x = 0; x < len; x++)
        printf("%c", buf[x]);
      printf ("\n");
#endif
      result = true;
    }

  close (fd);

}

int main ()
{
  char buf[5] = {0};
  bool result = false;

  if (get_code (buf, sizeof(buf)))

    {
      if (TSS_SUCCESS == extend_pcr (buf, sizeof(buf)))
        {
          result = true;
        }
    }

  return (result) ? EXIT_SUCCESS : EXIT_FAILURE;

}
