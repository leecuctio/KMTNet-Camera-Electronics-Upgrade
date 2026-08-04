#define SCSI_OFF sizeof(struct sg_header)

#include "Caliban.h"
#include <scsi/sg.h>  // Generic SCSI interface header for Linux 

// process a complete scsi cmd. Use the generic scsi interface. 

static int 
handle_scsi_cmd(unsigned cmd_len,         // command length 
		unsigned in_size,         // input data size 
		unsigned char *i_buff,    // input buffer 
		unsigned out_size,        // output data size 
		unsigned char *o_buff,    // output buffer 
		int fd                    // file descriptor 
		)
{
  int status = 0;
  struct sg_header *sg_hd;

  // safety checks 

  if (!cmd_len) return -1;            // need a cmd_len != 0 
  if (!i_buff) return -1;             // need an input buffer != NULL 
#ifdef SG_BIG_BUFF
  if (SCSI_OFF + cmd_len + in_size > SG_BIG_BUFF) return -1;
  if (SCSI_OFF + out_size > SG_BIG_BUFF) return -1;
#else
  if (SCSI_OFF + cmd_len + in_size > 4096) return -1;
  if (SCSI_OFF + out_size > 4096) return -1;
#endif
  
  if (!o_buff) out_size = 0;

  // generic scsi device header construction 

  sg_hd = (struct sg_header *) i_buff;
  sg_hd->reply_len   = SCSI_OFF + out_size;
  sg_hd->twelve_byte = cmd_len == 12;
  sg_hd->result = 0;
#if     0
  sg_hd->pack_len    = SCSI_OFF + cmd_len + in_size; // not necessary 
  sg_hd->pack_id;     // not used 
  sg_hd->other_flags; // not used 
#endif
  
  // send command 
  status = write( fd, i_buff, SCSI_OFF + cmd_len + in_size );
  if ( status < 0 || status != SCSI_OFF + cmd_len + in_size ||
       sg_hd->result ) {
    // some error happened 
    fprintf( stderr, "write(generic) result = 0x%x cmd = 0x%x\n",
	     sg_hd->result, i_buff[SCSI_OFF] );
    perror("");
    return status;
  }
  
  if (!o_buff) o_buff = i_buff;       // buffer pointer check 
  
  // retrieve result 
  status = read( fd, o_buff, SCSI_OFF + out_size);
  if ( status < 0 || status != SCSI_OFF + out_size || sg_hd->result ) {
    // some error happened 
    fprintf( stderr, "read(generic) result = 0x%x cmd = 0x%x\n",
	     sg_hd->result, o_buff[SCSI_OFF] );
    fprintf( stderr, "read(generic) sense "
	     "%x %x %x %x %x %x %x %x %x %x %x %x %x %x %x %x\n",
	     sg_hd->sense_buffer[0],         sg_hd->sense_buffer[1],
	     sg_hd->sense_buffer[2],         sg_hd->sense_buffer[3],
	     sg_hd->sense_buffer[4],         sg_hd->sense_buffer[5],
	     sg_hd->sense_buffer[6],         sg_hd->sense_buffer[7],
	     sg_hd->sense_buffer[8],         sg_hd->sense_buffer[9],
	     sg_hd->sense_buffer[10],        sg_hd->sense_buffer[11],
	     sg_hd->sense_buffer[12],        sg_hd->sense_buffer[13],
	     sg_hd->sense_buffer[14],        sg_hd->sense_buffer[15]);
    if (status < 0)
      perror("");
  }
  // Look if we got what we expected to get 
  if (status == SCSI_OFF + out_size) status = 0; // got them all 
  
  return status;  // 0 means no error 
}

long 
SGread (int fd, char *buf, long numbytes)
{
  unsigned char cmd[SCSI_OFF + 18];
  unsigned char CBReadbuffer[ SCSI_OFF + numbytes + 512];
  unsigned char cmdblk[6]; // 6 = opcode command block length 
  
  long blk;
  unsigned char lsb, sb, msb, lng;

  blk = ((systab->sgloc) / 512);
  
  lsb = blk & 0xFF;
  sb  = (blk >> 8) & 0xFF;
  msb = (blk >> 16) & 0x1F;
  
  lng = (numbytes/512) + 1;
  
  cmdblk[0] = 0x08;  // operation code (0x08 = read)          
  cmdblk[1] = msb;   // lun/logical block address msb         
  cmdblk[2] = sb;    // logical block address                 
  cmdblk[3] = lsb;   // logical block address lsb             
  cmdblk[4] = lng;   // transfer length (number of blocks)    
  cmdblk[5] = 0;     // vendor unique code/reserved/flag/link 
  
  memcpy( cmd + SCSI_OFF, cmdblk, sizeof(cmdblk) );

  // +------------------+
  // | struct sg_header | <- cmd
  // +------------------+
  // | copy of cmdblk   | <- cmd + SCSI_OFF
  // +------------------+
  
  if (handle_scsi_cmd(sizeof(cmdblk), 0, cmd,
		      sizeof(CBReadbuffer) - SCSI_OFF, CBReadbuffer, fd )) {
    fprintf( stderr, "CBRead failed\n" );
    exit(2);
  }
  
  memcpy(buf, CBReadbuffer + SCSI_OFF + ((systab->sgloc) % 512), numbytes);
  
  (systab->sgloc) += numbytes;
    
  return (strlen(buf));
  
}

void
SGseek(long bytepos)
{
  systab->sgloc = bytepos;
}
