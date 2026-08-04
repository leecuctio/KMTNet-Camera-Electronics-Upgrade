/* InitSocket Routine                                          */
/* Purpose: Socket device initialization                       */
/* Requires: Nothing                                           */
/* Returns: File descriptor upon success, zero upon failure    */

#include "Caliban.h"

int 
InitSocket()
{
  int sock;            /* Socket device file descriptor */

  static struct sockaddr_in server;
  static struct sockaddr_in client;
  struct hostent *host;

  /* resolve the ISIS server's hostname into an IP address */

  if (!(host=gethostbyname(systab->serverIPaddr))) {
    printf("ERROR: cannot resolve ISIS server hostname %s - %s\n",
	   systab->serverIPaddr,hstrerror(h_errno));
    printf("Caliban must abort...\n");
    exit(2);
  }

  /* setup the ISIS server's internet address structure */

  server.sin_family = AF_INET;
  server.sin_port = htons(systab->serverport);
  memcpy(&server.sin_addr,host->h_addr, host->h_length);

  /* save the 32-bit IP address of the server for later */

  systab->serveraddr = ntohl(server.sin_addr.s_addr);

  /* get a file descriptor for the client-side socket */

  if ((sock=socket(AF_INET,SOCK_DGRAM,0)) < 0 ) {
    printf("ERROR: cannot open network client socket - %s\n",
	   strerror(errno));
    printf("Caliban must abort...\n");
    exit(2);
  }

  /* setup Caliban's client-side internet address structure */

  client.sin_family = AF_INET;
  client.sin_addr.s_addr = htonl(INADDR_ANY);  /* generic "any" address */
  client.sin_port = htons(systab->clientport); 

  /* bind our client-side socket to this host:port */

  if (bind(sock, (struct sockaddr *) &client, sizeof(client)) < 0) {
    printf("ERROR: cannot bind network client socket to port %d - %s\n",
	   systab->clientport,strerror(errno));
    printf("Caliban must abort...\n");
    exit(2);
  }

  /* success, brag a bit... */

  printf("Initialized client socket on port %d\n",systab->clientport);

  return(sock); 

}
