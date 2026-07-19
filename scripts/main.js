const fs = require('fs');
const path = require('path');

const files = fs.readdirSync('pmon');

const buf = fs.readFileSync(path.join('pmon', files[3]));

const hexToDecimal = (hexString) => parseInt(parseInt(hexString, 16), 10);
const hexToBinary = (hexString) => parseInt(parseInt(hexString, 16), 2);

const cuttedBuf = buf.toString('hex').slice(32, buf.toString('hex').length);

const getPmonItem = (data, index) => data.substr(index * 60, 60)

const getYear = (buf) => hexToDecimal(`${buf.substr(14, 2)}${buf.substr(12, 1)}`);

const getMonth = (buf) => hexToDecimal(`${buf.substr(13, 1)}`);

const getDay = (buf) => hexToDecimal(`${buf.substr(10, 2)}`) % 248 >> 3;

// const getMinutes = (buf) => hexToDecimal(`0${parseInt((hexToDecimal(`${buf.substr(10, 2)}`) % 7), 16)}${buf.substr(8, 2)}`);
const getMinutes = (buf) => hexToDecimal(`${buf.substr(10, 2)}`).toString(2);

const getBufArray = () => {
    const bufArray = [];
    for (let i = 0; i < Math.round(cuttedBuf.length / 60); i++) {
        const pmonItem = getPmonItem(cuttedBuf, i);
        bufArray.push(`${pmonItem}: ${getMinutes(pmonItem)}.${getDay(pmonItem)}.${getMonth(pmonItem)}.${getYear(pmonItem)}`);
    }

    // const date = new Date(2022, 7, 30, 16, 9, 0);

    return bufArray;
}

fs.writeFileSync(`${files[3]}-bites.txt`, getBufArray());
