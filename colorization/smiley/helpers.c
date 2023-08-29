#include "helpers.h"

void colorize(int height, int width, RGBTRIPLE image[height][width])
{
    //comb through the rows and columns
    for (int i = 0; i < height; i++)
    {
        for (int r = 0; r < width; r++)
        {
            // Make black pixels to purple
            if (image[i][r].rgbtRed == 0x00 && image[i][r].rgbtGreen == 0x00 && image[i][r].rgbtBlue == 0x00)
            {
                image[i][r].rgbtRed = 0xaa;
                image[i][r].rgbtBlue = 0xdd;
            }
        }
    }
}
